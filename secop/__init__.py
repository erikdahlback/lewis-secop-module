from lewis.devices import Device
from lewis.adapters.epics import EpicsAdapter, PV

from secop.loggers import initLogging

initLogging(rootlevel='debug')

from secop.client.baseclient import Client

framework_version = '1.0.2'


class SecopDevice(Device):
    dummy = 10.0

    def __init__(self, host, port):
        super(SecopDevice, self).__init__()

        self._sc = Client({'connectto': host, 'port': port}, autoconnect=False)
        self._sc.startup(async=True)
        self.log.info('Modules: %s', self._sc.modules)


class SecopEpicsInterface(EpicsAdapter):
    def _bind_device(self):
        self.pvs = {}

        for module in self.device._sc.modules:
            for param in self.device._sc.getParameters(module):
                def create_getter(mod, par):
                    def getter(obj):
                        return self.device._sc.queryCache(mod, par).value

                    return getter

                def create_setter(mod, par):
                    def setter(obj, value):
                        return self.device._sc.setParameter(mod, par, value)

                    return setter

                attr_name = module + '_' + param
                #
                self.log.info('Installing property on interface: %s', attr_name)
                #
                setattr(type(self), attr_name, property(create_getter(module, param), create_setter(module, param)))
                #
                self.pvs[module + ':' + param] = PV(attr_name)

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
