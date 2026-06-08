'''
Created on 01.07.2022
LucidControl DI4DO4 Digital USB Module implementation
@author: Klaus Ummenhofer
'''
from lucidIo.LucidControl import LucidControl
from lucidIo.Cmd import Cmd
from lucidIo.Values import ValueDI1, ValueCNT2
from lucidIo.LucidControlDI import LucidControlDI
from lucidIo.LucidControlDI import LCDIMode
from lucidIo.LucidControlDI import _LCDIFlag

from lucidIo.LucidControlDO import LucidControlDO
from lucidIo.LucidControlDO import LCDOMode
from lucidIo.LucidControlDO import _LCDOFlag

from lucidIo import IoReturn
import struct

class LCDIDODeviceType(object):
    NONE                 = (0, "NONE")
    DI_5_DO_SSR          = (0x4000, "DI 5V / DO SSR")
    DI_10_DO_SSR         = (0x4001, "DI 10V / DO SSR")
    DI_24_DO_SSR         = (0x4005, "DI 24V / DO SSR")

class _LCDIDOParamAddress(object):
    DI_VALUE            = 0x1400
    DI_MODE             = 0x1500
    DI_FLAGS            = 0x1501
    DI_SCAN_TIME        = 0x1511
    DI_COUNT_TIME       = 0x1512
    DO_VALUE            = 0x1800
    DO_MODE             = 0x1900
    DO_FLAGS            = 0x1901
    DO_CYCLE_TIME       = 0x1910
    DO_DUTY_CYCLE       = 0x1911
    DO_ON_DELAY         = 0x1912
    DO_ON_HOLD          = 0x1913


class LucidControlDI4DO4(LucidControl):
    """LucidControl DI4DO4 Digital USB Module class
    """

    def getIo(self, channel, value):
        """Get the value or state of one digital IO channel.
            
        This method calls the GetIo function of the module and returns
        the value or of the digital IO channel.
        
        Args:
            channel: IO channel number.
            Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            value: Digital value object of type ValueDI1 or ValueCNT2.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(value, (ValueDI1, ValueCNT2)):
            raise TypeError('Expected value as ValueDI1 or ValueCNT2, \
                got {}'.format(type(value)))

        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')

        cmd = Cmd(self.com)
        return cmd.getIo(channel, value)


    def getIoGroup(self, channels, values):
        """Get the values of a group of digital IO channels.
            
        This method calls the GetIoGroup function of the module and
            returns the values of a group of input channels.
        
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only read if the corresponding channel is
                true.
            values: Digital values.
                A tuple with 8 digital value objects of type ValueDI1 or
                ValueCNT2. The function fills the objects with read data.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channels, tuple):
            raise TypeError('Expected channels as a tuple \
                (bools), got {}'.format(type(channels)))

        if (len(channels) != self.nrOfChannels):
            raise TypeError('Expected {} channels, got {}'.format(
                self.nrOfChannels, len(channels)))
        
        for x in range(self.nrOfChannels):
            if not isinstance(channels[x], int):
                raise TypeError('Expected channel as bool, got {}'.format(
                    type(channels[x])))

        if not isinstance(values, tuple):
            raise TypeError('Expected values as a tuple, got {}'.format(
                    type(values)))

        if (len(values) != self.nrOfChannels):
            raise TypeError('Expected {} values, got {}'.format(
                self.nrOfChannels, len(values)))

        for x in range(self.nrOfChannels):
            if not isinstance(values[x], (ValueDI1, ValueCNT2)):
                raise TypeError('Expected value as ValueDI1 or ValueCNT2, \
                    got {}'.format(type(values[x])))

        cmd = Cmd(self.com)
        return cmd.getIoGroup(channels, values)

    def setIo(self, channel, value):
        """Write the value or state of one digital output channel.
        
        This method calls the SetIo function of the module and writes
            the value or state of the digital output channel.
            
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
                value: Digital value object of type ValueDI1, initialized
                with the updated data.
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(value, ValueDI1):
            raise TypeError('Expected value as ValueDI1, got {}'.format(
                type(value)))
            
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        cmd = Cmd(self.com)
        return cmd.setIo(channel, value)

    def setIoGroup(self, channels, values):
        """Write values or states of a group of digital output channels.
        
        This method calls the SetIoGroup function of the module and
            writes the values or states of a group of output channels.
            
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only written if the corresponding channel is
                true.
            values: Digital values.
                A tuple with digital value objects. The values of the
                objects are written to the output channels.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channels, tuple):
            raise TypeError('Expected channels as tuple \
                (bools), got {}'.format(type(channels)))
        
        if (len(channels) != self.nrOfChannels):
            raise TypeError('Expected {} channels, got {}'.format(
                self.nrOfChannels, len(channels)))
        
        for x in range(self.nrOfChannels):
            if not isinstance(channels[x], int):
                raise TypeError('Expected channel as bool, got {}'.format(
                    type(channels[x])))
            
        if not isinstance(values, tuple):
            raise TypeError('Expected values as tuple, got {}'.format(
                type(values)))
        
        if (len(values) != self.nrOfChannels):
            raise TypeError('Expected {} values, got {}'.format(
                self.nrOfChannels, len(values)))
        
        for x in range(self.nrOfChannels):
            if not isinstance(values[x], ValueDI1):
                raise TypeError('Expected values as ValueDI1, got {}'.format(
                    type(values[x])))
            
        cmd = Cmd(self.com)
        return cmd.setIoGroup(channels, values)

    def getParamValue(self, channel, value):
        """Get the Configuration Parameter "Value" of a digital
            IO channel.
            
        This method calls the GetParam function of the module and returns
            the value of the Configuration Parameter "Value".
        
        The Configuration Parameter "Value" contains the current
        value of the input channel.
        
        It is recommended to call getIo instead of this method.
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            value: Digital value object of type ValueDI1.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(value, ValueDI1):
            raise TypeError('Expected value as ValueDI1, got {}'.format(
                type(value)))
            
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)

        if (channel < self.nrOfDIChannels):
            ret = cmd.getParam(_LCDIDOParamAddress.DI_VALUE, channel, data)
        else:
            ret = cmd.getParam(_LCDIDOParamAddress.DO_VALUE, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            value.setData(data)
        return ret

    def setParamValueDefault(self, channel, persistent):
        """Set the Configuration Parameter "Value" of a digital
            output channel to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Value" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
               
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DO_VALUE,
            channel, persistent)

    
    def setParamValue(self, channel, persistent, value):
        """Set the Configuration Parameter "Value" of a digital output channel.

        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Value".

        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            value: Digital value object of type ValueDI1.

        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(value, ValueDI1):
            raise TypeError('Expected value as ValueDI1, got {}'.format(
                type(value)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')

        data = bytearray()
        cmd = Cmd(self.com)
        
        value.getData(data)
        return cmd.setParam(_LCDIDOParamAddress.DO_VALUE, channel, persistent, data)


    def getParamDIMode(self, channel, mode):
        """Get the Configuration Parameter "Mode" of the digital input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            mode: Operation Mode as a list with one LCDIMode integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(mode, list):
            raise TypeError('Expected mode as list, got {}'.format(
                type(mode)))
        
        if len(mode) < 1:
            raise TypeError('Expected mode as list with 1 int, got {}'.format(
                len(mode)))
        
        if not isinstance(mode[0], int):
            raise TypeError('Expected mode[0] as int, got {}'.format(
                type(mode[0])))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')     

        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_MODE, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] == LCDIMode.INACTIVE:
                mode[0] = LCDIMode.INACTIVE
            elif data[0] == LCDIMode.REFLECT_VALUE:
                mode[0] = LCDIMode.REFLECT_VALUE
            elif data[0] == LCDIMode.RISING_EDGE:
                mode[0] = LCDIMode.RISING_EDGE
            elif data[0] == LCDIMode.FALLING_EDGE:
                mode[0] = LCDIMode.FALLING_EDGE
            elif data[0] == LCDIMode.COUNT:
                mode[0] = LCDIMode.COUNT
            else:
                mode[0] = LCDIMode.INACTIVE

        return ret

    def getParamDOMode(self, channel, mode):
        """Get the Configuration Parameter "Mode" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number.
               Channel numbers 4 - 7 refer to digital output channels DO0 - DO3 
            mode: Operation Mode as a list with one LCDOMode integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(mode, list):
            raise TypeError('Expected mode as list, got {}'.format(
                type(mode)))
        
        if len(mode) < 1:
            raise TypeError('Expected mode as list with 1 int, got {}'.format(
                len(mode)))
        
        if not isinstance(mode[0], int):
            raise TypeError('Expected mode[0] as int, got {}'.format(
                type(mode[0])))
            
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_MODE, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] == LCDOMode.INACTIVE:
                mode[0] = LCDOMode.INACTIVE
            elif data[0] == LCDOMode.REFLECT_VALUE:
                mode[0] = LCDOMode.REFLECT_VALUE
            elif data[0] == LCDOMode.ON_OFF:
                mode[0] = LCDOMode.ON_OFF
            elif data[0] == LCDOMode.CYCLE:
                mode[0] = LCDOMode.CYCLE
            else:
                mode[0] = LCDOMode.INACTIVE
        
        return ret

    def setParamDIMode(self, channel, persistent, mode):
        """Set the Configuration Parameter "Mode" of a digital
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCDIMode integer value
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range    
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))

        if not isinstance(mode, int):
            raise TypeError('Expected mode as int, got {}'.format(
                type(mode)))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')

        data = bytearray([mode])

        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DI_MODE, channel, persistent, data)


    def setParamDOMode(self, channel, persistent, mode):
        """Set the Configuration Parameter "Mode" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCDOMode integer value
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range    
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(mode, int):
            raise TypeError('Expected mode as int, got {}'.format(
                type(mode)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        data = bytearray([mode])
        
        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DO_MODE, channel, persistent, data)

    def setParamModeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Mode" of a digital IO
            channel to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Mode" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)

        if (channel >= self.nrOfDIChannels):
            return cmd.setParamDefault(_LCDIDOParamAddress.DO_MODE, channel, persistent)
        else:
            return cmd.setParamDefault(_LCDIDOParamAddress.DI_MODE, channel, persistent)
      

    def setParamFlagsDefault(self, channel, persistent):
        """Set the Configuration Parameter "Flags" of a digital
            IO channel to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Flags" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))

        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')   

        cmd = Cmd(self.com)

        if (channel >= self.nrOfDIChannels):
            return cmd.setParamDefault(_LCDIDOParamAddress.DO_FLAGS, channel, persistent)
        else:
            return cmd.setParamDefault(_LCDIDOParamAddress.DI_FLAGS, channel, persistent)


    def getParamDIFlagAddCounter(self, channel, addCounter):
        """Get the Configuration Parameter Flag "Add Counter" of the digital input channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Add Counter".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            addCounter: Parameter Flag "Add Counter" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(addCounter, list):
            raise TypeError('Expected addCounter as list, got {}'.format(
                type(addCounter)))
            
        if len(addCounter) < 1:
            raise TypeError('Expected addCounter as list with 1 bool, got {}'.format(
                len(addCounter)))
        
        if not isinstance(addCounter[0], int):
            raise TypeError('Expected addCounter[0] as bool, got {}'.format(
                type(addCounter[0])))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')

        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDIFlag.ADD_COUNTER:
                addCounter[0] = True
            else:
                addCounter[0] = False
        return ret


    def setParamFlagAddCounter(self, channel, persistent, addCounter):
        """Set the Configuration Parameter Flag "Add Counter" of the digital input channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Add Counter".
        
         Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            addCounter: Parameter Flag "Add Counter" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))

        if not isinstance(addCounter, bool):
            raise TypeError('Expected addCounter as bool, got {}'.format(
                type(addCounter)))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')

        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDIFlag.ADD_COUNTER
            if (addCounter == True):
                data[0] |= _LCDIFlag.ADD_COUNTER

            ret = cmd.setParam(_LCDIDOParamAddress.DI_FLAGS, channel, persistent, data)

        return ret

    
    def getParamDIFlagResetCounterRead(self, channel, resetCounterRead):
        """Get the Configuration Parameter Flag "Reset Counter on Read" of the digital
            input channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Reset Counter on Read".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            resetCounterRead: Parameter Flag "Reset Counter on Read"
                as a list containing one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(resetCounterRead, list):
            raise TypeError('Expected resetCounterRead as list, got {}'.format(
                type(resetCounterRead)))
            
        if len(resetCounterRead) < 1:
            raise TypeError('Expected resetCounterRead as list with 1 bool, \
                got {}'.format(len(resetCounterRead)))
        
        if not isinstance(resetCounterRead[0], int):
            raise TypeError('Expected resetCounterRead[0] as bool, got {}'.format(
                type(resetCounterRead[0])))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')

        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDIFlag.RESET_COUNTER_READ:
                resetCounterRead[0] = True
            else:
                resetCounterRead[0] = False
        return ret


    def setParamDIFlagResetCounterRead(self, channel, persistent,
        resetCounterRead):
        """Set the Configuration Parameter Flag "Reset Counter on Read" of the digital
            input channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Reset Counter on Read".
        
         Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            resetCounterRead: Parameter Flag 
                "Reset Counter on Read" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))

        if not isinstance(resetCounterRead, bool):
            raise TypeError('Expected resetCounterRead as bool, got {}'.format(
                type(resetCounterRead)))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')          

        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDIFlag.RESET_COUNTER_READ
            if (resetCounterRead == True):
                data[0] |= _LCDIFlag.RESET_COUNTER_READ

        ret = cmd.setParam(_LCDIDOParamAddress.DI_FLAGS, channel, persistent, data)
        return ret


    def getParamDIFlagInverted(self, channel, inverted):
        """Get the Configuration Parameter Flag "Inverted" of the digital input channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Inverted".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            inverted: Parameter Flag "Inverted" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(inverted, list):
            raise TypeError('Expected inverted as list, got {}'.format(
                type(inverted)))
            
        if len(inverted) < 1:
            raise TypeError('Expected inverted as list with 1 bool, got {}'.format(
                len(inverted)))
        
        if not isinstance(inverted[0], int):
            raise TypeError('Expected inverted[0] as bool, got {}'.format(
                type(inverted[0])))

        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')

        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDIFlag.INVERTED:
                inverted[0] = True
            else:
                inverted[0] = False
        return ret
 
    
    def setParamDIFlagInverted(self, channel, persistent, inverted):
        """Set the Configuration Parameter Flag "Inverted" of the digital input channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Inverted".
        
         Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            inverted: Parameter Flag "Inverted" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(inverted, bool):
            raise TypeError('Expected inverted as bool, got {}'.format(
                type(inverted)))
        
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')
        
        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDIFlag.INVERTED
            if (inverted == True):
                data[0] |= _LCDIFlag.INVERTED
        
        ret = cmd.setParam(_LCDIDOParamAddress.DI_FLAGS, channel, persistent, data)
        
        return ret


    def getParamDIScanTime(self, channel, scanTime):
        """Get the Configuration Parameter "Scan Time" of the digital input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Scan Time".
          
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            scanTime: Parameter "Scan Time" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(scanTime, list):
            raise TypeError('Expected scanTime as list, got {}'.format(
                type(scanTime)))
        
        if len(scanTime) < 1:
            raise TypeError('Expected scanTime as list with 1 int, got {}'.format(
                len(scanTime)))
        
        if not isinstance(scanTime[0], int):
            raise TypeError('Expected scanTimel[0] as int, got {}'.format(
                type(scanTime[0])))
            
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_SCAN_TIME, channel, data)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            scanTime[0] = struct.unpack("<I", data)[0]
        else:
            scanTime[0] = 0
            
        return ret
        
    
    def setParamDIScanTimeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Scan Time" of a digital
            input to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Scan Time" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DI_SCAN_TIME, channel,
            persistent)
    
    
    def setParamDIScanTime(self, channel, persistent, scanTime):
        """Set the Configuration Parameter "Scan Time" of a digital
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Scan Time".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            scanTime: Parameter "Scan Time" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or cycleTime value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(scanTime, int):
            raise TypeError('Expected scanTime as int, got {}'.format(
                type(scanTime)))
        
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')
        
        if (scanTime < 0) | (scanTime >= pow(2, 32)):
            raise ValueError('Scan Time out of range')

        data = bytearray(struct.pack("<I", scanTime))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DI_SCAN_TIME,
            channel, persistent, data) 


    def getParamDICountTime(self, channel, countTime):
        """Get the Configuration Parameter "Count Time" of the digital input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Count Time".
          
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            countTime: Parameter "Count Time" as a list containing one
                integer value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(countTime, list):
            raise TypeError('Expected countTime as list, got {}'.format(
                type(countTime)))
        
        if len(countTime) < 1:
            raise TypeError('Expected countTime as list with 1 int, got {}'.format(
                len(countTime)))
        
        if not isinstance(countTime[0], int):
            raise TypeError('Expected countTime[0] as int, got {}'.format(
                type(countTime[0])))
            
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DI_COUNT_TIME, channel, data)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            countTime[0] = struct.unpack("<I", data)[0]
        else:
            countTime[0] = 0
            
        return ret
        
    
    def setParamDICountTimeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Count Time" of a digital
            input to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Count Time" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DI_COUNT_TIME, channel, persistent)
    
    
    def setParamDICountTime(self, channel, persistent, countTime):
        """Set the Configuration Parameter "Count Time" of a digital
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Count Time".
        
        Args:
            channel: IO channel number.
                Channel numbers 0 - 3 refer to digital input channels DI0 - DI3
            persistent: Store parameter permanently if true
            countTime: Parameter "Count Time" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or cycleTime value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistant as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(countTime, int):
            raise TypeError('Expected countTime as int, got {}'.format(
                type(countTime)))
        
        if (channel >= self.nrOfDIChannels):
            raise ValueError('Channel out of range')
        
        if (countTime < 0) | (countTime >= pow(2, 32)):
            raise ValueError('Count Time out of range')

        data = bytearray(struct.pack("<I", countTime))
        cmd = Cmd(self.com)
        
        return cmd.setParam(_LCDIDOParamAddress.DI_COUNT_TIME, channel, persistent, data)         

    def getParamDOFlagCanCancel(self, channel, canCancel):
        """Get the Configuration Parameter Flag "Can Cancel" of the digital output channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Can Cancel".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            canCancel: Parameter Flag "Can Cancel" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(canCancel, list):
            raise TypeError('Expected canCancel as list, got {}'.format(
                type(canCancel)))
            
        if len(canCancel) < 1:
            raise TypeError('Expected canCancel as list with 1 bool, got {}'.format(
                len(canCancel)))
        
        if not isinstance(canCancel[0], int):
            raise TypeError('Expected canCancel[0] as bool, got {}'.format(
                type(canCancel[0])))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDOFlag.CAN_CANCEL:
                canCancel[0] = True
            else:
                canCancel[0] = False
        return ret         
        
    
    def setParamDOFlagCanCancel(self, channel, persistent, canCancel):
        """Set the Configuration Parameter Flag "Can Cancel" of the digital output channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Can Cancel".
        
         Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            canCancel: Parameter Flag "Can Cancel" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(canCancel, bool):
            raise TypeError('Expected canCancel as bool, got {}'.format(
                type(canCancel)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')          
        
        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDOFlag.CAN_CANCEL
            if (canCancel == True):
                data[0] |= _LCDOFlag.CAN_CANCEL
                
            ret = cmd.setParam(_LCDIDOParamAddress.DO_FLAGS, channel,
                persistent, data)
        
        return ret
    
    def getParamDOFlagCanRetrigger(self, channel, canRetrigger):
        """Get the Configuration Parameter Flag "Can Retrigger" of the digital output channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Can Retrigger".
        
        Args:
             channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            canRetrigger: Parameter Flag "Can Retrigger" as a list containing
                one boolean value
                
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(canRetrigger, list):
            raise TypeError('Expected canRetrigger as list, got {}'.format(
                type(canRetrigger)))
            
        if len(canRetrigger) < 1:
            raise TypeError('Expected canRetrigger as list with 1 bool, got {}'.format(
                len(canRetrigger)))
        
        if not isinstance(canRetrigger[0], int):
            raise TypeError('Expected canRetrigger[0] as bool, got {}'.format(
                type(canRetrigger[0])))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDOFlag.CAN_RETRIGGER:
                canRetrigger[0] = True
            else:
                canRetrigger[0] = False
        return ret         


    def setParamDOFlagCanRetrigger(self, channel, persistent, canRetrigger):
        """Set the Configuration Parameter Flag "Can Retrigger" of the digital output channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Can Retrigger".
        
         Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            canRetrigger: Parameter Flag "Can Retrigger" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(canRetrigger, bool):
            raise TypeError('Expected canRetrigger as bool, got {}'.format(
                type(canRetrigger)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')          
        
        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDOFlag.CAN_RETRIGGER
            if (canRetrigger == True):
                data[0] |= _LCDOFlag.CAN_RETRIGGER
        
        ret = cmd.setParam(_LCDIDOParamAddress.DO_FLAGS, channel, persistent, data)
        return ret
    
    
    
    def getParamDOFlagInverted(self, channel, inverted):
        """Get the Configuration Parameter Flag "Inverted" of the digital output channel.
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Inverted".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            inverted: Parameter Flag "Inverted" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(inverted, list):
            raise TypeError('Expected inverted as list, got {}'.format(
                type(inverted)))
            
        if len(inverted) < 1:
            raise TypeError('Expected inverted as list with 1 bool, got {}'.format(
                len(inverted)))
        
        if not isinstance(inverted[0], int):
            raise TypeError('Expected inverted[0] as bool, got {}'.format(
                type(inverted[0])))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] & _LCDOFlag.INVERTED:
                inverted[0] = True
            else:
                inverted[0] = False
        return ret         
 
    
    def setParamDOFlagInverted(self, channel, persistent, inverted):
        """Set the Configuration Parameter Flag "Inverted" of the digital output channel.
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Inverted".
        
         Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            inverted: Parameter Flag "Inverted" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(inverted, bool):
            raise TypeError('Expected inverted as bool, got {}'.format(
                type(inverted)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')          
        
        # Read current flags
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_FLAGS, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            data[0] &= ~_LCDOFlag.INVERTED
            if (inverted == True):
                data[0] |= _LCDOFlag.INVERTED
        
        ret = cmd.setParam(_LCDIDOParamAddress.DO_FLAGS, channel, persistent, data)
        return ret


    
    def getParamDOCycleTime(self, channel, cycleTime):
        """Get the Configuration Parameter "Cycle Time" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Cycle Time".
          
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            cycleTime: Parameter "Cycle Time" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(cycleTime, list):
            raise TypeError('Expected cycleTime as list, got {}'.format(
                type(cycleTime)))
        
        if len(cycleTime) < 1:
            raise TypeError('Expected cycleTime as list with 1 int, got {}'.format(
                len(cycleTime)))
        
        if not isinstance(cycleTime[0], int):
            raise TypeError('Expected cycleTime[0] as int, got {}'.format(
                type(cycleTime[0])))
            
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_CYCLE_TIME, channel, data)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            cycleTime[0] = struct.unpack("<I", data)[0]
        else:
            cycleTime[0] = 0
            
        return ret
        
    
    def setParamDOCycleTimeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Cycle Time" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Cycle Time" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DO_CYCLE_TIME,
            channel, persistent)
    
    
    
    def setParamDOCycleTime(self, channel, persistent, cycleTime):
        """Set the Configuration Parameter "Cycle Time" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Cycle Time".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            cycleTime: Parameter "Cycle Time" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or cycleTime value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(cycleTime, int):
            raise TypeError('Expected cycleTime as int, got {}'.format(
                type(cycleTime)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        if (cycleTime < 0) | (cycleTime >= pow(2, 32)):
            raise ValueError('Cycle Time out of range')

        data = bytearray(struct.pack("<I", cycleTime))
        cmd = Cmd(self.com)
        
        return cmd.setParam(_LCDIDOParamAddress.DO_CYCLE_TIME, channel,
            persistent, data) 


        
    
    def getParamDODutyCycle(self, channel, dutyCycle):
        """Get the Configuration Parameter "Duty Cycle" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Duty Cycle".
          
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            dutyCycle: Parameter "Duty Cycle" as a list containing one integer
                value  (Duty Cycle as 1/1000)
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(dutyCycle, list):
            raise TypeError('Expected dutyCycle as list, got {}'.format(
                type(dutyCycle)))
        
        if len(dutyCycle) < 1:
            raise TypeError('Expected dutyCycle as list with 1 int, got {}'.format(
                len(dutyCycle)))
        
        if not isinstance(dutyCycle[0], int):
            raise TypeError('Expected dutyCycle[0] as int, got {}'.format(
                type(dutyCycle[0])))
            
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_DUTY_CYCLE, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            dutyCycle[0] = struct.unpack("<H", data)[0]
        else:
            dutyCycle[0] = 0
        return ret
        
        
    
    def setParamDODutyCycleDefault(self, channel, persistent):
        """Set the Configuration Parameter "Duty Cycle" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Duty Cycle" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DO_DUTY_CYCLE, channel,
            persistent)
    
    
    
    def setParamDODutyCycle(self, channel, persistent, dutyCycle):
        """Set the Configuration Parameter "Duty Cycle" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Duty Cycle".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            dutyCycle: Parameter "Duty Cycle" in 1/1000
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or dutyCycle value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(dutyCycle, int):
            raise TypeError('Expected dutyCycle as int, got {}'.format(
                type(dutyCycle)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        if (dutyCycle < 0) | (dutyCycle > 1000):
            raise ValueError('DutyCycle out of range')
        
        data = bytearray(struct.pack("<H", dutyCycle))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DO_DUTY_CYCLE, channel,
            persistent, data) 
    
    
    
    def getParamDOOnHold(self, channel, onHold):
        """Get the Configuration Parameter "On Hold" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "On Hold".
          
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            onHold: Parameter "On Hold" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(onHold, list):
            raise TypeError('Expected onHold as list, got {}'.format(
                type(onHold)))
        
        if len(onHold) < 1:
            raise TypeError('Expected onHold as list with 1 int, got {}'.format(
                len(onHold)))
        
        if not isinstance(onHold[0], int):
            raise TypeError('Expected onHold[0] as int, got {}'.format(
                type(onHold[0])))
            
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_ON_HOLD, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            onHold[0] = struct.unpack("<I", data)[0]
        else:
            onHold[0] = 0
        return ret    



    def setParamDOOnHoldDefault(self, channel, persistent):
        """Set the Configuration Parameter "On Hold" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "On Hold" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DO_ON_HOLD,
            channel, persistent)
    
    
    
    def setParamDOOnHold(self, channel, persistent, onHold):
        """Set the Configuration Parameter "On Hold" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "On Hold".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            onHold: Parameter "On Hold" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or onHold value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(onHold, int):
            raise TypeError('Expected onHold as int, got {}'.format(
                type(onHold)))
    
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        if (onHold < 0) | (onHold >= pow(2, 32)):
            raise ValueError('On Hold out of range')
        
        data = bytearray(struct.pack("<I", onHold))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DO_ON_HOLD, channel,
            persistent, data) 
    
    
    
    def getParamDOOnDelay(self, channel, onDelay):
        """Get the Configuration Parameter "On Delay" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "On Delay".
          
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            onDelay: Parameter "On Delay" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
            
        if not isinstance(onDelay, list):
            raise TypeError('Expected onDelay as list, got {}'.format(
                type(onDelay)))
        
        if len(onDelay) < 1:
            raise TypeError('Expected onDelay as list with 1 int, got {}'.format(
                len(onDelay)))
        
        if not isinstance(onDelay[0], int):
            raise TypeError('Expected onDelay[0] as int, got {}'.format(
                type(onDelay[0]))) 

        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCDIDOParamAddress.DO_ON_DELAY, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            onDelay[0] = struct.unpack("<I", data)[0]
        else:
            onDelay[0] = 0
        return ret



    def setParamDOOnDelayDefault(self, channel, persistent):
        """Set the Configuration Parameter "On Delay" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "On Delay" to the default value.
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')   
        
        cmd = Cmd(self.com)
        return cmd.setParamDefault(_LCDIDOParamAddress.DO_ON_DELAY, channel,
            persistent)

    
    def setParamDOOnDelay(self, channel, persistent, onDelay):
        """Set the Configuration Parameter "On Delay" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "On Delay".
        
        Args:
            channel: IO channel number.
                Channel numbers 4 - 7 refer to digital output channels DO0 - DO3
            persistent: Store parameter permanently if true
            onDelay: Parameter "On Delay" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or onDelay value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(onDelay, int):
            raise TypeError('Expected onDelay as int, got {}'.format(
                type(onDelay)))
        
        if ((channel >= self.nrOfChannels) or (channel < self.nrOfDIChannels)):
            raise ValueError('Channel out of range')

        if (onDelay < 0) | (onDelay >= pow(2, 32)):
            raise ValueError('On Delay out of range')

        data = bytearray(struct.pack("<I", onDelay))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCDIDOParamAddress.DO_ON_DELAY, channel,
            persistent, data) 
    
   
    def getDeviceTypeName(self):
        """Get device type name as string.
        
        Returns:
            String of the device type name
        
        Raises:
            ValueError: ID data not valid
        """
        if self.id.validData == True:
            if (self.id.deviceType == LCDIDODeviceType.DI_5_DO_SSR[0]):
                return LCDIDODeviceType.DI_5_DO_SSR[1]
            elif (self.id.deviceType == LCDIDODeviceType.DI_10_DO_SSR[0]):
                return LCDIDODeviceType.DI_10_DO_SSR[1]
            elif (self.id.deviceType == LCDIDODeviceType.DI_24_DO_SSR[0]):
                return LCDIDODeviceType.DI_24_DO_SSR[1]
            else:
                return "Not Identified"
        else:
            return "Not valid"

    def getDeviceType(self):
        """Get device type.
        
        Returns:
            Device type
        """
        if (self.id.validData == True):
            return self.id.deviceType
        else:
            return LCDIDODeviceType.NONE

                
    def __init__(self, portName):
        """
        Constructor of LucidControl Digital IO USB Module class
        """
        LucidControl.__init__(self, portName)
        self.nrOfChannels = 8
        self.nrOfDIChannels = 4