'''
Created on Jan 3, 2010

@author: chris
'''
from nec.common.address import RoutingAddress
from nec.common.service import ReactorService
from nec.protocol.routing import RoutingProtocol, ViewerRequest
import sys
import traceback
from Tkinter import *
from PIL import Image
import ImageTk
from cStringIO import StringIO
import base64

class StreamViewer(Frame):
     def __init__(self, root):
        root.title("Test Application")
        self.addFrame(root)

     def addFrame(self,root):
          frame = Frame(root,  background="#FFFFFF")
          self.addCanvas(frame)
          frame.pack(fill=BOTH, expand=YES)

     def addCanvas(self, frame):
        self.canvas = Canvas(frame, background='#000000')
        self.canvas.pack(fill=BOTH, expand=YES)
        self.canvas.pack()

     def addImage(self, photoimage, size):
          self.canvas.create_image(size[0],size[1], image=photoimage,anchor=SE)

class ViewerService(ReactorService):
    def __init__(self,
                  viewerAddress,
                  mediaRouterAddress,
                  generatorAddresses,
                  **kwargs):
        super(ViewerService, self).__init__(**kwargs)

        self.viewerAddress = viewerAddress
        self.mediaRouterAddress = mediaRouterAddress
        self.generatorAddresses = generatorAddresses

        self.routingProtocol = None
        self.root = Tk()
        self.sv = StreamViewer(self.root)

    def prepare(self):
        self.routingProtocol = RoutingProtocol.forViewer(self.viewerAddress,
                                                         self._deliveredDataReceived)
        self.routingProtocol.connectToReactor(self.reactor)

    def run(self):
        print '%s is running' % self.__class__.__name__

        routedData = ViewerRequest(self.viewerAddress,
                                   self.generatorAddresses)
        self.routingProtocol.sendData(routedData,
                                      self.mediaRouterAddress)

    def _deliveredDataReceived(self, deliveredData):
#        print deliveredData.payload
        dataReceived = base64.b64decode(deliveredData.payload)
        buff = StringIO(dataReceived)
        im = Image.open(buff)
        siz = im.size
	imagetk = ImageTk.PhotoImage(im)
	self.sv.addImage(imagetk, siz)
	self.root.update()


def parseArgs(args):
    usage = 'usage: %s VIEWER_ADDRESS:PORT MEDIA_ROUTER_ADDRESS:PORT GENERATOR_ADDRESS:PORT [...]' % sys.argv[0]

    assert len(sys.argv) > 3, usage

    try:
        viewerAddress = RoutingAddress.fromString(sys.argv[1])
        mediaRouterAddress = RoutingAddress.fromString(sys.argv[2])
        generatorAddresses = set(RoutingAddress.fromString(addressString)
                                 for addressString in sys.argv[3:])

        return (viewerAddress,
                mediaRouterAddress,
                generatorAddresses)

    except Exception:
        traceback.print_exc()
        print
        print usage

        sys.exit(1)

def main():
    (viewerAddress,
     mediaRouterAddress,
     generatorAddresses) = parseArgs(sys.argv)

    service = ViewerService(viewerAddress,
                            mediaRouterAddress,
                            generatorAddresses,
                            loggingEnabled = False)
    service.start()

if __name__ == '__main__':
    main()
