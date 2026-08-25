# Save format notes

`tmp2` is a binary plist using NSKeyedArchiver. The supplied analysis reports that `tmp3` is two MD5 hex strings concatenated. The first is `MD5("222" + hex(MD5(tmp2)) + "333")`; the second is based on `NSFileSystemFileNumber`. ZIP import of a 64-character tag compares only the first 32 characters.
