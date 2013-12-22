#! -*- encoding: utf-8 -*-

import copy
import csv
import hashlib
import os
import sqlite3
import struct
import sys
import uuid

from Cocoa import NSArchiver
from Cocoa import NSMutableAttributedString
from Cocoa import NSNumber
from Cocoa import NSString
apple_absolute_time_since = 978307200


number_country = {'+86': 'cn'}
handle_chat_ids = {}


def get_attributedBody(text):
    string = NSMutableAttributedString.alloc()
    string = string.initWithString_attributes_(
                                text, {u'__kIMMessagePartAttributeName':
                                                NSNumber.numberWithInt_(0)})
    return unicode(NSString.alloc().initWithData_encoding_(
                            NSArchiver.archivedDataWithRootObject_(string), 1))


def get_string(data, offset):
    size = struct.unpack('>H', data[offset:offset + 2])[0]
    if size == 0xffff:
        return None, offset + 2
    return data[offset + 2:offset + 2 + size], offset + 2 + size


def update_mbdb(filepath, sha1, size):
    content = open(filepath, 'rb').read()
    if content[:6] != 'mbdb\x05\x00':
        print('Wrong mbdb format')
        sys.exit(1)
    offset = 6
    f = None
    while offset < len(content):
        domain, offset = get_string(content, offset)
        path, offset = get_string(content, offset)
        link_target, offset = get_string(content, offset)
        if domain == 'HomeDomain' and path == 'Library/SMS/sms.db':
            f = open(filepath, 'r+b')
            f.seek(offset + 2)
            f.write(sha1)
        data_hash, offset = get_string(content, offset)
        unknown, offset = get_string(content, offset)
        # mode
        offset += 2
        # unknown
        offset += 8
        # userid
        offset += 4
        # groupid
        offset += 4
        # time1, time2, time3
        offset += 4 * 3
        if f:
            f.seek(offset)
            f.write(struct.pack('>Q', size))
            f.close()
            return
        # size
        offset += 8
        # flag
        offset += 1
        # property count
        property_count = ord(content[offset])
        offset += 1
        for i in range(property_count):
            name, offset = get_string(content, offset)
            value, offset = get_string(content, offset)



def update_old_message(cursor, old_ids, next_date):
    """Update old messages' ids whose date is before next_date to the latest
    one.

    If next_date is None, update all the old_ids.
    """
    tmp_ids = copy.copy(old_ids)
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'message'")
    last_rowid = cursor.fetchone()[0]
    for old_id, date in tmp_ids:
        if date > next_date and next_date is not None:
            break
        last_rowid += 1
        cursor.execute("UPDATE message SET ROWID = %s WHERE ROWID = %s" %
                       (last_rowid, old_id))
        cursor.execute("UPDATE chat_message_join SET message_id = %s "
                        "WHERE message_id = %s" % (last_rowid, old_id))
        old_ids.pop(0)
    cursor.execute("UPDATE sqlite_sequence SET seq = %s "
                    "WHERE name = 'message'" % last_rowid)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('File not found')
        sys.exit(1)
    if not (os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2])):
        print('File not found')
        sys.exit(1)
    f = open(sys.argv[2], 'rb')
    reader = csv.reader(f)
    conn = sqlite3.connect(sys.argv[1])
    cursor = conn.cursor()
    # get the latest available number as the sender's number
    cursor.execute("SELECT account_id, account_login FROM chat "
                    "WHERE service_name = 'SMS' "
                      "AND account_login LIKE 'P:%' "
                 "ORDER BY ROWID DESC "
                    "LIMIT 1")
    result = cursor.fetchone()
    if not result:
        print('No available number found, have one message sent at least')
        sys.exit(1)
    account_id, account_login = result

    cursor.execute("SELECT ROWID, date FROM message")
    old_ids = cursor.fetchall()

    for row in reader:
        number, send, date, text = row
        send = False if send == '1' else True
        date = int(date) - apple_absolute_time_since
        update_old_message(cursor, old_ids, date)
        text = text.decode('utf-8')
        country = 'cn'
        for prefix, country_ in number_country.items():
            if number.startswith(prefix):
                country = country_
                break

        if number in handle_chat_ids:
            handle_id, chat_id = handle_chat_ids[number]
        else:
            new = False
            cursor.execute("SELECT ROWID FROM handle WHERE id = '%s' "
                              "AND service = 'SMS'" % number)
            result = cursor.fetchone()
            if not result:
                cursor.execute("INSERT INTO handle "
                                  "(id, country, service, uncanonicalized_id) "
                            "VALUES ('%s', '%s', '%s', '%s')" %
                            (number, country, 'SMS', number))
                handle_id = cursor.lastrowid
                new = True
            else:
                handle_id = result[0]

            cursor.execute("SELECT ROWID FROM chat "
                            "WHERE chat_identifier = '%s' "
                              "AND service_name = 'SMS'" % row[0])
            result = cursor.fetchone()
            if not result:
                cursor.execute("INSERT INTO chat "
                               "(guid, style, state, account_id, "
                                 "chat_identifier, service_name, "
                                 "account_login) "
                               "VALUES ('%s', %s, %s, '%s', '%s', 'SMS', '%s')"
                               % ('SMS;-;%s' % number, 45, 3, account_id,
                                  number, account_login))
                chat_id = cursor.lastrowid
                new = True
            else:
                chat_id = result[0]
            if new:
                cursor.execute("INSERT INTO chat_handle_join VALUES (%s, %s)" %
                            (chat_id, handle_id))

        if send:
            date_read = 0
            date_delivered = 0
            is_delivered = 0
            is_from_me = 1
            is_read = 0
            is_sent = 1
            has_dd_results = 0
        else:
            date_read = 0
            date_delivered = 0
            is_delivered = 1
            is_from_me = 0
            is_read = 1
            is_sent = 0
            has_dd_results = 0
        cursor.execute("INSERT INTO message ("
                         "guid, text, replace, handle_id, attributedBody, "
                         "version, service, account, account_guid, date, "
                         "date_read, date_delivered, is_delivered, "
                         "is_finished, is_from_me, is_read, is_sent, "
                         "has_dd_results, was_data_detected) "
                       "VALUES ('%s', ?, 0, '%s', ?, 10, 'SMS', '%s', "
                               "'%s', %s, %s, %s, %s, 1, %s, %s, %s, %s, 1)" %
                       (str(uuid.uuid4()).upper(), handle_id,
                        account_login.lower(), account_id, date, date_read,
                        date_delivered, is_delivered, is_from_me, is_read,
                        is_sent, has_dd_results),
                       (text, get_attributedBody(text)))
        message_id = cursor.lastrowid
        cursor.execute("INSERT INTO chat_message_join VALUES (%s, %s)" %
                       (chat_id, message_id))
        conn.commit()
    if old_ids:
        update_old_message(cursor, old_ids, None)
        conn.commit()
    f.close()
    conn.close()
    sha1 = hashlib.sha1(open(sys.argv[1], 'rb').read()).digest()
    size = os.stat(sys.argv[1]).st_size - 16384
    update_mbdb(sys.argv[3], sha1, size)

