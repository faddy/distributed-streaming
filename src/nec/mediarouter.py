'''
Created on Dec 28, 2009

@author: chris
'''

from nec.common.address import RoutingAddress
from nec.common.service import ReactorService
from nec.protocol.routing import RoutingProtocol, ViewerRequest, GeneratedData
import sys
import traceback
import Image
from cStringIO import StringIO
import base64

class Task(object):
    def __init__(self, taskCount, viewerAddress, downstreamRequestedGenerators, upstreamRequestedGenerators, mediaRouterServiceObj):
        self.taskCount = taskCount
        self.viewerAddress = viewerAddress
        self.downstreamRequestedGenerators = downstreamRequestedGenerators
        self.upstreamRequestedGenerators = upstreamRequestedGenerators
        self.data = {}
        self.mediaRouterServiceObj = mediaRouterServiceObj
        self.upstreamDummyAddress = RoutingAddress('upstream',100000)

        for generator in self.downstreamRequestedGenerators:
            self.data[generator] = None
        if len(self.upstreamRequestedGenerators)>0:
            self.data[self.upstreamDummyAddress] = None

    def getData(self, routedData):
        print 'getData() for viewer: %s --> ' % self.viewerAddress
        routedDataGenerators = set(routedData.sourceAddress)

        dataReceived = base64.b64decode(routedData.payload)
        buff = StringIO(dataReceived)
        imageObj = Image.open(buff)
        # if routedData has come from upstreamGenerators
        if routedDataGenerators == self.upstreamRequestedGenerators:
            self.data[self.upstreamDummyAddress] = imageObj
            print 'upstream data added to data dictionary'
        else:
        # if routedData has come from downstreamGenerators
            for generatorAddress in routedData.sourceAddress:
                # add data from requested generators to a dictionary
                self.data[generatorAddress] = imageObj
            print 'downstream data added to data dictionary'

        print 'data dictionary for viewer: %s --> '%self.viewerAddress, self.data
        
        if (self.data.values().count(None)==0):
        # process data if data from all generators is received
            routedData = self.combine()
            print 'After combine(): '
            self.sendCombinedData(routedData)
        
    def combine(self):
        print 'combine() for viewer: %s'%self.viewerAddress
        newImage = Image.new("RGB",((len(self.data))*200,150))
        offset = 0
        newPayload = ""
        newSourceAddresses = []
        newDataReceived = ""

        # update payload
        for key in self.data:
#            buff = StringIO(self.data[key])
#            im = Image.open(buff)
#            im = Image.open(StringIO(self.data[key]))
            newImage.paste(self.data[key],(offset,0))
            offset += 100
        newImage = newImage.resize((200,150))
        newDataReceived = newImage.tostring("jpeg",('RGB',))
        newPayload = base64.b64encode(newDataReceived)
        # update the generator address 'list'
        for x in self.downstreamRequestedGenerators:
            newSourceAddresses.append(x)
        for x in self.upstreamRequestedGenerators:
            newSourceAddresses.append(x)

        newData = GeneratedData(newSourceAddresses.pop(), newPayload)
        for x in newSourceAddresses:
            newData.sourceAddress.append(x)

        for key in self.data:
            self.data[key] = None

        return newData

    def sendCombinedData(self, routedData):
        deliveredData = routedData.asDeliveredData()
        for x in deliveredData.sourceAddress:
            deliveredData.sourceAddress = x
        
        print 'sending the combined data for Task: %s-%s' %(str(self.taskCount), str(self.viewerAddress))
        self.mediaRouterServiceObj._deliverData(deliveredData, self.viewerAddress)

class StreamObject(object):
    def __init__(self, generatorAddresses):
        self.generatorSet = generatorAddresses

class MediaRouterService(ReactorService):

    def __init__(self,
                  sourceAddress,
                  destinationAddress,
                  **kwargs):

        self.taskCount = 0
        super(MediaRouterService, self).__init__(**kwargs)

        # Routing members
        self.sourceAddress = sourceAddress
        self.destinationAddress = destinationAddress

        self.routingProtocol = None

        # Data handling members
        self.downstreamGenerators = set()

        # Task mappings
        self.generatorTasks = {}    # generator-tasks
        self.viewerTasks = {}       # viewer-task

    @property
    def shortIdentifier(self):
        return '%s_%s_' % (self.__class__.__name__,
                           self.sourceAddress)


    def prepare(self):
        '''Prepare the RoutingProtocol.'''
        self.routingProtocol = RoutingProtocol.forMediaRouter(self.sourceAddress,
                                                              self._viewerRequestReceived,
                                                              self._generatedDataReceived,
                                                              self._deliveredDataReceived)
        self.routingProtocol.connectToReactor(self.reactor)

    def run(self):
        print 'Running %s' % self.__class__.__name__

    def _viewerRequestReceived(self, routedData):
        print '####################################################'
        
        viewerAddress = routedData.sourceAddress
        for v in viewerAddress:
            viewer = v
        print 'received viewer request from %s' % viewerAddress
        print routedData.payload

        requestedGenerators = routedData.payload
        print 'viewer requested generators: %s' % requestedGenerators

        downstreamRequestedGenerators = self.downstreamGenerators.intersection(requestedGenerators)

        upstreamRequestedGenerators = requestedGenerators.difference(downstreamRequestedGenerators)
        print 'upstreamRequestedGenerators: %s' % upstreamRequestedGenerators

        
        # if a Task object already exists for this viewer, delete it from the viewer-task dictionary.
##        for viewer in viewerAddress:
##            if self.viewerTasks.has_key(viewer):
##                print 'deleting Task for earlier request from viewer: %s' %viewer
##                del self.viewerTasks[viewer]

        # create a task object for this viewer and add it to the viewer-task dictionary
        self.taskCount+=1
        task = Task(self.taskCount, viewer, downstreamRequestedGenerators, upstreamRequestedGenerators, self)
        #self.viewerTasks[viewer] = task
        #print 'viewerTasks dictionary --> '
        #for k in self.viewerTasks:
         #   print str(k) +":", self.viewerTasks[k]

        #streamObj = StreamObject()

        for g in downstreamRequestedGenerators:
            for stream in self.generatorTasks:
                if stream.generatorSet==set([g]):
                    self.generatorTasks[stream].add(task)

        print 'generatorTask dictionary --> '
        for k in self.generatorTasks:
            out = ''
            for i in self.generatorTasks[k]:
                out += str(i.taskCount) + "-" + str(i.viewerAddress) + " "
            print k.generatorSet, out

        if len(upstreamRequestedGenerators)==0:
            return

        for stream in self.generatorTasks:
            print stream.generatorSet, upstreamRequestedGenerators
            if stream.generatorSet==upstreamRequestedGenerators:
                self.generatorTasks[stream].add(task)
                return

        stream = StreamObject(upstreamRequestedGenerators)
        self.generatorTasks[stream]=set()
        self.generatorTasks[stream].add(task)

        upstreamRequest = ViewerRequest(self.sourceAddress, upstreamRequestedGenerators)
        

#        for g in requestedGenerators:
#            # if the generator-tasks mapping table does not have entry for the generator requested, add it to the generator-tasks mapping table
#            if g not in self.generatorTasks:
#                self.generatorTasks[g] = set()
#
#            # map this generator to the task (generator-tasks dictionary)
#            self.generatorTasks[g].add(task)

        #print 'add generator %s : task %s to generatorTask dictionary' % (g, task.viewerAddress)

        print 'generatorTask dictionary --> '
        for k in self.generatorTasks:
            out = ''
            for i in self.generatorTasks[k]:
                out += str(i.taskCount) + "-" + str(i.viewerAddress) + " "
            print k.generatorSet, out

        if self.destinationAddress:
            self.routingProtocol.sendData(upstreamRequest, self.destinationAddress)
            print 'forwarded upstream request'
        else:
            print 'WARNING: upstream generators %s do not exist!' % upstreamRequestedGenerators

    def _generatedDataReceived(self, routedData):
        print '------------------------------------------------------'
        print 'generatedDataReceived from %s' % routedData.sourceAddress

        setGeneratorAddress = set(routedData.sourceAddress)
        streamObj = StreamObject(setGeneratorAddress)
        print streamObj.generatorSet
        print routedData.sourceAddress.__sizeof__(), routedData.payload.__sizeof__()

        # Add this generator to our known downstream generators set
        if (setGeneratorAddress.intersection(self.downstreamGenerators))==set([]):
            self.downstreamGenerators.update(setGeneratorAddress)
            print 'adding to downstream generators set', setGeneratorAddress
            self.generatorTasks[streamObj] = set()

        # forward data to the next hop if necessary
        if self.destinationAddress:
            #print 'forwarding generated data up to', self.destinationAddress
            self.routingProtocol.sendData(routedData, self.destinationAddress)

        
        for stream in self.generatorTasks:
            print stream.generatorSet
            if stream.generatorSet==setGeneratorAddress:
                #print 'match found'
                if self.generatorTasks[stream]==set([]):
                    print 'Source %s has not been requested for delivery requests yet.' % setGeneratorAddress
                    return
                else:
                    for task in self.generatorTasks[stream]:
                        print 'Calling getData for task: %s-%s' % (task.taskCount, task.viewerAddress)
                        task.getData(routedData)
                        

    def _deliveredDataReceived(self, deliveredData):
        print '======================================================'
        # deliveredDataReceived will have more than one generator in sourceAddress
        print '_deliveredDataReceived from: %s' % deliveredData.sourceAddress
        print deliveredData

        for stream in self.generatorTasks:
            print stream.generatorSet, set(deliveredData.sourceAddress)
            if stream.generatorSet==set(deliveredData.sourceAddress):
                for task in self.generatorTasks[stream]:
                    task.getData(deliveredData)
                return

    def _deliverData(self, deliveredData, viewerAddress):
        print "deliverData() for viewer --> %s" %viewerAddress
        
#        for generatorAddress in deliveredData.sourceAddress:
#            if self.generatorTasks.has_key(generatorAddress)!=1:
#                print 'Source %s has not been registered for delivery requests.' % generatorAddress
#                return

        #print 'data from %s requested by %s' % (deliveredData.sourceAddress, requestingViewer)

#        print 'delivering data to %s: %s' % (viewerAddress, deliveredData)
        self.routingProtocol.sendData(deliveredData, viewerAddress)

        print '***** finished for viewer %s *****' %viewerAddress


def parseArgs(args):
    try:
        usage = 'usage: %s SRC_ADDRESS:PORT [DST_ADDRESS:PORT]' % sys.argv[0]

        assert len(args) >= 2, usage

        sourceAddress = RoutingAddress.fromString(sys.argv[1])
        destinationAddress = RoutingAddress.fromString(sys.argv[2]) if len(args) > 2 else None


        return (sourceAddress,
                destinationAddress)

    except Exception:
        traceback.print_exc()
        print
        print usage

        sys.exit(1)


def main():
    (source,
     destination) = parseArgs(sys.argv)

    service = MediaRouterService(source, destination, loggingEnabled = True)
    service.start()


if __name__ == '__main__':
    main()
