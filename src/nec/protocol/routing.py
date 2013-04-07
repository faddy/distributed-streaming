'''
Created on Dec 28, 2009

@author: chris
'''

from twisted.internet.protocol import DatagramProtocol
import pickle


class RoutedData(object):
    '''Represents a message of routed data.'''

    class MessageType(object):
        VIEWER_REQUEST = 'viewer_request'
        GENERATED_DATA = 'generated_data'
        DELIVERED_DATA = 'delivered_data'

    def __init__(self,
                  sourceAddress,
                  messageType,
                  payload):

        # The sourceAddress indicates where the routed data
        # was originally constructed.
        self.sourceAddress = [sourceAddress]

        # The messageType indicates how this message should be treated
        self.messageType = messageType

        # Keep track of the path the message took
        # (This is mostly for debugging purposes, but may come in handy for
        #    routing algorithms in the future as well.)
        self.messagePath = []

        # The payload is the data for the routed message
        self.payload = payload



    @classmethod
    def fromNetwork(cls, data):
        '''Deserialize data from a string recieved from the network.
        
        Note that this is an inherently *unsafe* operation, as we 
        are executing code passed to us from the network. For production
        usage, the interface must be hardened.
        '''
        return pickle.loads(data)

    def toNetwork(self, sendingAddress):
        '''Serialize data to a string suitable for network sending.'''
        self.messagePath.append(sendingAddress)
        return pickle.dumps(self)

    def __str__(self):
        '''Return a string representation of the routed data.'''
        return '<%s %s>' % (self.__class__.__name__,
                            ' '.join('%s=%s' % (k, v)
                                     for k, v in self.__dict__.items()
                                     if not k.startswith('_')))

class ViewerRequest(RoutedData):
    def __init__(self,
                  sourceAddress,
                  payload):
        super(ViewerRequest, self).__init__(sourceAddress,
                                            self.MessageType.VIEWER_REQUEST,
                                            payload)

class DeliveredData(RoutedData):
    def __init__(self,
                  sourceAddress,
                  payload):
        super(DeliveredData, self).__init__(sourceAddress,
                                            self.MessageType.DELIVERED_DATA,
                                            payload)

class GeneratedData(RoutedData):
    def __init__(self,
                  sourceAddress,
                  payload):
        super(GeneratedData, self).__init__(sourceAddress,
                                            self.MessageType.GENERATED_DATA,
                                            payload)

    def asDeliveredData(self):
        return DeliveredData(self.sourceAddress,
                             self.payload)



class RoutingProtocol(DatagramProtocol):
    '''Protocol describing routed data.'''

    class ProtocolConsumer(object):
        VIEWER = 0
        GENERATOR = 1
        MEDIA_ROUTER = 2

    @classmethod
    def forViewer(cls,
                   viewerAddress,
                   deliveredDataReceivedCallback):
        return RoutingProtocol(consumerType = cls.ProtocolConsumer.VIEWER,
                               localAddress = viewerAddress,
                               deliveredDataReceivedCallback = deliveredDataReceivedCallback)

    @classmethod
    def forGenerator(cls,
                      generatorAddress):
        return RoutingProtocol(consumerType = cls.ProtocolConsumer.GENERATOR,
                               localAddress = generatorAddress)

    @classmethod
    def forMediaRouter(cls,
                         mediaRouterAddress,
                         viewerRequestReceivedCallback,
                         generatedDataReceivedCallback,
                         deliveredDataReceivedCallback):
        return RoutingProtocol(consumerType = cls.ProtocolConsumer.MEDIA_ROUTER,
                               localAddress = mediaRouterAddress,
                               viewerRequestReceivedCallback = viewerRequestReceivedCallback,
                               generatedDataReceivedCallback = generatedDataReceivedCallback,
                               deliveredDataReceivedCallback = deliveredDataReceivedCallback)

    def __init__(self,
                  consumerType,
                  localAddress,
                  viewerRequestReceivedCallback = None,
                  generatedDataReceivedCallback = None,
                  deliveredDataReceivedCallback = None):
        self.consumerType = consumerType
        self.localAddress = localAddress

        if self.consumerType == self.ProtocolConsumer.MEDIA_ROUTER:
            assert callable(viewerRequestReceivedCallback), 'MediaRouter consumers must provide a viewerRequestReceivedCallback function.'
            assert callable(generatedDataReceivedCallback), 'MediaRouter consumers must provide a generatedDataReceivedCallback function.'

        self.viewerRequestReceivedCallback = viewerRequestReceivedCallback
        self.generatedDataReceivedCallback = generatedDataReceivedCallback

        if self.consumerType in (self.ProtocolConsumer.MEDIA_ROUTER,
                                 self.ProtocolConsumer.VIEWER):
            assert callable(deliveredDataReceivedCallback)
        self.deliveredDataReceivedCallback = deliveredDataReceivedCallback

    def connectToReactor(self, reactor):
        udpPort = reactor.listenUDP(self.localAddress.port,
                                    self,
                                    interface = self.localAddress.host)
#        print 'Bound to port: %s' % udpPort

    def datagramReceived(self, data, (host, port)):
        '''Handle data recieved from the network.
        
        This method is called by the Twisted framework when data becomes
        available.
        '''
        # deserialize the data
        routedData = RoutedData.fromNetwork(data)
#        print 'received data from %s:%s: %s' % (host, port, routedData)

        # push the message up to media router consumers
        if self.consumerType == self.ProtocolConsumer.MEDIA_ROUTER:
            if routedData.messageType == RoutedData.MessageType.VIEWER_REQUEST:
                self.viewerRequestReceivedCallback(routedData)
            elif routedData.messageType == RoutedData.MessageType.GENERATED_DATA:
                self.generatedDataReceivedCallback(routedData)


        if self.consumerType in (self.ProtocolConsumer.MEDIA_ROUTER,
                                 self.ProtocolConsumer.VIEWER):
            if routedData.messageType == RoutedData.MessageType.DELIVERED_DATA:
                self.deliveredDataReceivedCallback(routedData)

    def sendData(self, routedData, destinationAddress):
        '''Send data to the provided address.'''
#        print 'sending data to %s: %s' % (destinationAddress, routedData)
        self.transport.write(routedData.toNetwork(self.localAddress),
                             destinationAddress.asTuple())
