'''
Created on Jan 3, 2010

@author: chris
'''

class RoutingAddress(object):
    '''Helper class to provide address parsing.'''

    @classmethod
    def fromString(cls, addressString):
        host, port = addressString.split(':')
        return RoutingAddress(host, port)

    def __init__(self, host, port):
        assert host
        assert port

        self.host = host
        self.port = int(port)

    def asTuple(self):
        return (self.host, self.port)

    def __str__(self):
        return '%s:%s' % (self.host, self.port)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__str__())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.host == other.host and
                    self.port == other.port)

        return False

    def __hash__(self):
        return hash(self.asTuple())
