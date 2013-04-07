'''
Created on Dec 28, 2009

@author: chris
'''

from nec.common.service import ReactorService
from nec.protocol.routing import RoutingProtocol, GeneratedData
from nec.common.address import RoutingAddress
import sys
import traceback
from PIL import Image
from cStringIO import StringIO
import base64


class GeneratorService(ReactorService):

    def __init__(self,
                  generatorAddress,
                  routerAddress,
                  dataGenerationIntervalMs = 100,
                  **kwargs):
        super(GeneratorService, self).__init__(**kwargs)

        self.generatorAddress = generatorAddress
        self.routerAddress = routerAddress

        self.file = open("/home/nec/movie.Mjpeg", "rb")
#        self.s = self.file.read()
#        self.im = Image.open(StringIO(self.s))
#        self.file.close()
        self.routingProtocol = None

        # TODO: ideally, identifier would be a command line argument, not the port number
        self.identifier = self.generatorAddress.port
        self.increment = 0
        self.dataGenerationIntervalMs = dataGenerationIntervalMs

    @property
    def shortIdentifier(self):
        return '%s_%s_' % (self.__class__.__name__, self.generatorAddress)


    def prepare(self):
        '''Prepare the routing protocol.'''
        self.routingProtocol = RoutingProtocol.forGenerator(self.generatorAddress)
        self.routingProtocol.connectToReactor(self.reactor)

    def run(self):
        self.sendForever()

    def sendForever(self):
        # change the routedData to create GeneratedData from the self.image object insted of self.increment
#        routedData = GeneratedData(self.generatorAddress,
#                                   '%s-%s' % (self.identifier, self.increment))

        l = int(self.file.read(5))
        s = self.file.read(l)
#        print s
        im = Image.open(StringIO(s))
        im = im.resize((200,150))
#        im1 = im.resize((64,64))
#        payload = {}
#        payload['size'] = im.size
#        payload['mode'] = im.mode
#        payload['data'] = im
        test_str = im.tostring("jpeg",('RGB',))
        data = base64.b64encode(test_str)

#        print len(data)
#        data = str(data)
        routedData = GeneratedData(self.generatorAddress, data)
        print routedData
        print self.generatorAddress.__sizeof__(), test_str.__sizeof__(), data.__sizeof__()
#        print routedData
#        print "sending: %s" % routedData
        self.routingProtocol.sendData(routedData,self.routerAddress)
#        self.increment += 1
#        print self.file.tell()
#        print s
        print "data sent successfully!"
        self.reactor.callLater(self.dataGenerationIntervalMs / 1000.0,
                               self.sendForever)
        print "reactor.callater done!"


def parseArgs(args):
    usage = 'usage: %s SRC_INTERFACE_ADDRESS:PORT DST_ADDRESS:PORT' % sys.argv[0]

    assert len(args) == 3, usage

    try:
        sourceAddress = RoutingAddress.fromString(sys.argv[1])
        destinationAddress = RoutingAddress.fromString(sys.argv[2])

        return (sourceAddress, destinationAddress)

    except Exception:
        traceback.print_exc()
        print
        print usage

        sys.exit(1)


def main():
    (source, destination) = parseArgs(sys.argv)

    service = GeneratorService(source,
                               destination,
                               dataGenerationIntervalMs = 33,
                               loggingEnabled = True)
    service.start()

if __name__ == '__main__':
    main()
