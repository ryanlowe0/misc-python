#!/usr/local/bin/python

import os
import sys
import yaml
from odict import odict


DEFAULT_DIR = os.getenv('PLANT_CONFIG_DIR') or '/etc/mypub/'
PLANT_YAML = os.path.join(DEFAULT_DIR, 'plant.yml')


class ConfigError(Exception): pass


def parse_ini_file(ini):
    import ConfigParser
    parser = ConfigParser.RawConfigParser()
    parser.read(ini)
    d = {}
    sections = parser.sections()
    for s in parser.sections():
        d[s] = dict(parser.items(s))
    return d

def to_dict(d):
    ' Recursively convert tree of dict sub-classes to simple nested dict '
    newdict = {}
    for k, v in d.items():
        if k == '_filename':
            continue
        if isinstance(v, dict):
            newdict[k] = to_dict(v)
        else:
            newdict[k] = v
    return newdict
    

class Config(dict):
    ''' Config is a recursive odict structure.
        
        Nodes containing .yml paths as values are interpreted as references 
        to external configs when accessed, and are loaded as sub-trees. 
        
        Example:

        (yaml)

        imposition:
            metafile: /plant/var/impmeta.yml

        (usage)

        conf.imposition.metafile['classic-die']

    '''

    def __init__(self, indict={}):
        newdict = {}
        fn = ''
        if '_filename' in indict:
            fn = indict['_filename']
        for k, v in indict.items():
            if isinstance(v, dict):
                if fn:
                    v['_filename'] = fn
                newdict[k] = Config(v)
            else:
                newdict[k] = v
        dict.__init__(self, newdict)

    def __str__(self): 
        return yaml.dump(to_dict(self), indent=4,
                         default_flow_style=False)

    def __repr__(self):
        return repr(to_dict(self))

    def keys(self):
        return [k for k in dict.keys(self) if k <> '_filename']

    def allkeys(self):
        return [k for k in dict.keys(self)]

    def values(self):
        return [self[k] for k in dict.keys(self) if k <> '_filename']

    def items(self):
        return [(k, v) for k, v in dict.items(self) if k <> '_filename']

    def allitems(self):
        return [(k, v) for k, v in dict.items(self)]

    def __setattr__(self, key, value): 
        self[key] = value
    
    def __getattr__(self, key): 
        return self[key]

    def __getitem__(self, key):
        try:
            item = dict.__getitem__(self, key)
            if isinstance(item, str) and not key.startswith('_'):
                if item.endswith('.yml'):
                    return ConfigFile(item)
                if item.endswith('.ini'):
                    return Config(parse_ini_file(item))
        except KeyError:
            msg = "'%s' not defined in config" % key
            if '_filename' in self.allkeys():
                msg += " file '%s'" % self._filename
            raise ConfigError(msg)
        return item


class ConfigFile(Config):
    ' Load a Config from an external file '
    def __init__(self, filename):
        if filename.endswith('.ini') or filename.endswith('.conf'):
            d = parse_ini_file(filename)
        else:
            if not filename.endswith('.yml'):
                filename += '.yml'
            d = yaml.load(open(filename))
        d['_filename'] = filename
        Config.__init__(self, d)

    def save(self, filename=None):
        if not filename:
            filename = self._filename
        open(filename, 'w').write(str(self))
    

class PlantConfig(ConfigFile):
    ''' ConfigFile with the following special behavior:

        "root" is a special key specifying the location of another
          config which will replace the current one.

        "conf" is a special key specifying an additional config which
          will extend the current and root config and recursively 
          override any conflicting keys.
    '''
    def __init__(self):
        main = ConfigFile(PLANT_YAML)
        root = main.get('root', '')
        conf = main.get('conf', {})
        if conf:
            conf = ConfigFile(os.path.join(root, conf))
        if root:
            main = ConfigFile(os.path.join(root, os.path.basename(PLANT_YAML)))
            main.update(conf)
        self.update(main)



def test():
    """
    c = Config({'A': {'b': 1, 'c': 2, 'd': {'x':0,'xx':1,'xxx':3}}})
    print 'c =\n',c
    u = {'A': {'b': 2, 'e': 4, 'd': {'xx': 4}}}
    print '-'*30
    print 'u =\n',Config(u)
    c.update(u)
    print '-'*30
    print 'c =\n',c
    c.A.d.update({'bb':1, 'bbb':2})
    print '-'*30
    print 'c =\n',c
    """
    c = PlantConfig()
    print c.imposition.metadata.B
    print c.baditem



if __name__ == '__main__':
    test()
