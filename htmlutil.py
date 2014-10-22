#!/usr/local/bin/python

import sys
import urllib
from Crypto.Cipher import DES # note this is regular DES not triple DES (DES3)

PWD = 'Va1ha11a'

def encypher(**data):
    'Simple parameter obfuscation'
    data = ','.join(['%s=%s' % (k, v) for k, v in data.items()])
    new = ''
    for c in data: 
        new += chr(ord(c) + 1)
    return urllib.quote(new)

def decypher(s):
    data = ''
    for c in urllib.unquote(s):
        data += chr(ord(c) - 1)
    return dict([pair.split('=') for pair in data.split(',')])
            
            
class Encryption(object):
    # Switched from pyDes to Crypto for speed as the latter is written in C.
    # Unfortunately it doesn't automatically handle padding for you as pyDes did
    # So the pad / unpad code was borrowed from pyDes for PAD_PKCS5 mode.
    # Another thing is that we actually used regular DES instead of DES3 when
    # we initially implemented encryption so we're staying with that for now.
    
    def __init__(self, pwd=PWD):
        # Thoughts for the future - switch to DES3, use a better IV and pwd.
        self.pwd = pwd 

    def pad(self, data):
        # PAD_PKCS5 padding 
        pad_len = 8 - (len(data) % 8)
        return data + pad_len * chr(pad_len)

    def unpad(self, data):
        # PAD_PKCS5 unpadding 
        pad_len = ord(data[-1])
        return data[:-pad_len]

    # We cannot simply hold onto the DES object between calls like we did when
    # using pyDes with the self.key attribute as the object seems to get corrupt
    # after doing an encrypt or decrypt.  If you call the encrypt / decrypt
    # more than once on the same instance you get garbage prefixed onto the data
    def _key(self):
        return DES.new(self.pwd, DES.MODE_CBC, "\0"*8)
    key = property(_key)
    
    def encrypt(self, **data):
        'Robust parameter encryption'
        from base64 import encodestring as b64encode
        data = ['%s=%s' % (k, v) for k, v in data.items()]
        data = self.key.encrypt(self.pad(','.join(data)))
        return urllib.quote(b64encode(data))
        
    def decrypt(self, s):
        from base64 import decodestring as b64decode
        data = self.unpad(self.key.decrypt(b64decode(urllib.unquote(s))))
        return dict([pair.split('=') for pair in data.split(',')])

    def urlsafe_encrypt(self, **data):
        'Robust parameter encryption without + and / in base64.'
        from base64 import urlsafe_b64encode as b64encode
        data = ['%s=%s' % (k, v) for k, v in data.items()]
        data = self.key.encrypt(self.pad(','.join(data)))
        return b64encode(data)

    def urlsafe_decrypt(self, s):
        from base64 import urlsafe_b64decode as b64decode
        data = self.unpad(self.key.decrypt(b64decode(s)))
        return dict([pair.split('=') for pair in data.split(',')])

def test():
    x = encypher(sp=1, order_id=21345)
    print x
    print decypher(x)
    
    e = Encryption()
    x = e.encrypt(sp=1, order_id=21345)
    print x
    print e.decrypt(x)


def syntax(msg=None):
    if msg:
        print msg
        print
    print "htmlutil.py encrypt <string>"
    print "            decrypt <encrypted_string>"
    print "            test"
    sys.exit(1)
    
if __name__ == '__main__':
    try:
        cmd = sys.argv[1]
    except:
        syntax()
        
    if cmd == 'encrypt':
        from base64 import encodestring, b64encode
        try:
            string = sys.argv[2]
        except:
            syntax('cmd: %s - you must specify string.' % cmd)
        e=Encryption()            
        #print encodestring(e.key.encrypt(string))
        print b64encode(e.key.encrypt(string))
        
    elif cmd == 'decrypt':
        from base64 import decodestring 
        try:
            encrypted_string = sys.argv[2]
        except:
            syntax('cmd: %s - you must specify encrypted string.' % cmd)
        e=Encryption()
        print e.key.decrypt(decodestring(encrypted_string))
    elif cmd == 'test':
        test()
    else:
        syntax()
    
