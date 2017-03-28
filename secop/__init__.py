import threading
from time import sleep

from lewis.adapters.epics import EpicsAdapter, PV
from lewis.devices import Device
from secop.loggers import initLogging

initLogging(rootlevel='debug')

from secop.client.baseclient import Client

framework_version = '1.0.3'


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

    def get_properties(self, module, param):
        return self._sc.getProperties(module, param)


class SecopEpicsInterface(EpicsAdapter):
    type_map = {
        str: 'string',
        float: 'float',
        int: 'int'
    }

    def _bind_device(self):
        self.pvs = {}

        for module in self.device.modules:
            for param in self.device.get_parameters(module):
                param_properties = self.device.get_properties(module, param)
                param_type = self.type_map.get(param_properties['validator'], None)

                if param_type is not None:
                    pv_name = module + ':' + param
                    self.log.debug('Generating PV %s of type %s', pv_name, param_type)
                    self.pvs[pv_name] = PV(
                        (lambda modu=module, par=param: self.device.get_parameter(modu, par),
                         lambda value, modu=module, par=param: self.device.set_parameter(
                             modu, par, value)), type=param_type)
                else:
                    self.log.warn(
                        'Param %s of module %s has type that can not be mapped to EPICS: %s',
                        param, module, param_properties['validator'])

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
