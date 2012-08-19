from SimpleXMLRPCServer import SimpleXMLRPCServer

import threading

class XMLRPC(threading.Thread):
    def __init__(self, bot):
        super(XMLRPC, self).__init__()
        self.bot = bot

    def run(self):
        server = SimpleXMLRPCServer(("0.0.0.0", 8000))
        server.register_introspection_functions()

        server.register_function(self.handle_notify, 'notify')

        # Run the server's main loop
        server.serve_forever()

    # register a function under a different name
    def handle_notify(self, s):
        self.bot.say(s)
        return True

