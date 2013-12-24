Tested on iPhone 5S with iOS 7.0.4.

Back up, run the script on the backup, and restore the phone.

Initially, it's the tool to transfer sms in other devices backed up in csv format,
to iPhone. It's the restore process.

## TODO ##
By adding the backup process, I can now manipulate every detail of the message.

## Usage ##

```
python restore.py <sms database> <sms csv> Manifest.mbdb
```

- The filename of sms database is 3d0d7e5fb2ce288813306e4d4636395e047a3d28
- Sms database and Manifest.mbdb are in a folder in `~/Library/Application Support/MobileSync/Backup`
- Columns of sms csv (direction: 1 for inbound, 2 for outbound):

```
number,direction,unix timestamp,text
```

## Caveats ##

It now doesn't process country code prefix, like +86 in China. Numbers with or
without the prefix are different.

Also, it doesn't contain any country code than China yet.

For field `attributedBody`, nothing other than `__kIMMessagePartAttributeName` is added (the value is 0 for this as observed),
so the links will only show as plain text.

## Reference ##

- [An Overview of the Messages (OS X) Database Structure](http://joshgrochowski.com/overview-of-messages-database-structure/)
- [iTunes Backup](http://theiphonewiki.com/wiki/ITunes_Backup)
- [Messages - The iPhone Wiki](http://theiphonewiki.com/wiki/Messages)
- [MbdbMbdxFormat](https://code.google.com/p/iphonebackupbrowser/wiki/MbdbMbdxFormat)
