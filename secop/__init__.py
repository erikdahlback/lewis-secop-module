import threading
from time import sleep

from lewis.adapters.epics import EpicsAdapter, PV
from lewis.devices import Device
from secop.loggers import initLogging

initLogging(rootlevel='debug')

from secop.client.baseclient import Client

framework_version = '1.0.2'


def cmd_loop(write_cache, fn):
    while True:
        while write_cache:
            cmd = write_cache.pop(0)
            fn(*cmd)
        sleep(0.234)


class SecopDevice(Device):
    def __init__(self, host, port):
        super(SecopDevice, self).__init__()

        self._write_cache = []

        self._sc = Client({'connectto': host, 'port': port}, autoconnect=False)
        self._sc.startup(async=True)
        self.log.info('Modules: %s', self._sc.modules)

        self._thread = threading.Thread(target=cmd_loop,
                                        args=(self._write_cache, self._sc.setParameter))
        self._thread.daemon = True
        self._thread.start()

    @property
    def modules(self):
        return self._sc.modules

    def get_parameters(self, module):
        return self._sc.getParameters(module)

    def get_parameter(self, module, param):
        return self._sc.queryCache(module, param).value

    def set_parameter(self, module, param, value):
        self._write_cache.append((module, param, value))


class SecopEpicsInterface(EpicsAdapter):
    def _bind_device(self):
        self.pvs = {}

        for module in self.device.modules:
            for param in self.device.get_parameters(module):
                self.pvs[module + ':' + param] = PV(
                    (lambda modu=module, par=param: self.device.get_parameter(modu, par),
                     lambda value, modu=module, par=param: self.device.set_parameter(
                         modu, par, value)))

        super(SecopEpicsInterface, self)._bind_device()


setups = dict(
    default=dict(
        device_type=SecopDevice,
        parameters=dict(
            host='localhost',
            port=10767
        )
    )
)
