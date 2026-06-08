
#from _typeshed import Self
from lucidIo.LucidControl import LucidControl
from lucidIo.Cmd import Cmd
from lucidIo.Values import ValueANU2, ValueVOS2, ValueVOS4, ValueCUS4
from lucidIo import IoReturn
import struct

class LCAIMode(object):
    """Module Operation Mode values
    
    This class contains integer values representing the Operation
    Modes. They are supposed to be used with setParamMode and
    getParamMode commands. 
    """
    INACTIVE            = 0x00
    STANDARD            = 0x01

class LCAIDeviceType(object):
    AI_NONE     = (0x0000, "Not identified")
    AI_0_5      = (0x1000, "0 V ~ 5 V")
    AI_0_10     = (0x1001, "0 V ~ 10 V")
    AI_0_12     = (0x1002, "0 V ~ 12 V")
    AI_0_15     = (0x1003, "0 V ~ 15 V")
    AI_0_20     = (0x1004, "0 V ~ 20 V")
    AI_0_24     = (0x1005, "0 V ~ 24 V")
    AI_5_5      = (0x1010, "-5 V ~ 5 V")
    AI_10_10    = (0x1011, "-10 V ~ 10 V")
    AI_12_12    = (0x1012, "-12 V ~ 12 V")
    AI_15_15    = (0x1013, "-15 V ~ 15 V")
    AI_20_20    = (0x1014, "-20 V ~ 20 V")
    AI_24_24    = (0x1015, "-24 V ~ 24 V")
    AI_0_20MA_500 = (0x1110, "0 A ~ 0.02 A")

class _LCAIParamAddress(object):
    VALUE           = 0x1000
    MODE            = 0x1100
    FLAGS           = 0x1101
    NR_SAMPLES      = 0x1112
    OFFSET          = 0x1120

class LucidControlAI(LucidControl):
    """""LucidControl Analog Input USB Module class
    """

    def getIo(self, channel, value):
        """Get the value or state of an analog input channel.
            
        This method calls the GetIo function of the module and returns
        the value or of the analog input channel.
        
        Args:
            channel: IO channel number. Must be in valid range
            value: Value object. Must be either ValueVOS4, ValueVOS2,
                ValueCUS4 or ValueANU2
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance (channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance (value, (ValueANU2, ValueVOS2, ValueVOS4, ValueCUS4)):
            raise TypeError('Expected value as ValueANU2 or ValueVOS2, \
                ValueVOS4 or ValueCUS4 got {}'.format(type(value)))
         
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')

        cmd = Cmd(self.com)
        return cmd.getIo(channel, value)


    def getIoGroup(self, channels, values):
        """Get the values of a group of analog input channels.
            
        This method calls the GetIoGroup function of the module and
            returns the values of a group of analog input channels.
        
        Args:
            channels: Tuple with boolean values (one for each channel).
                A channel is only read if the corresponding channel is
                true.
            values: Value objects
                A tuple with analog value objects. The value objects must be
                either ValueVOS4, ValueVOS2, ValueCUS4 or ValueANU2.
                The function fills the objects with read data.
            
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
            raise TypeError('Expected {} channels, got {}'.format(self.nrOfChannels, len(channels)))
        
        for x in range(self.nrOfChannels):
            if not isinstance(channels[x], int):
                raise TypeError('Expected channel as bool, got {}'.format(
                    type(channels[x])))

        if not isinstance(values, tuple):
            raise TypeError('Expected values as a tuple, got {}'.format(
                type(values)))

        if (len(values) != self.nrOfChannels):
            raise TypeError('Expected {} values, got {}'.format(self.nrOfChannels, len(values)))

        for x in range(self.nrOfChannels):
            if not isinstance(values[x], (ValueANU2, ValueVOS2, ValueVOS4, ValueCUS4)):
                raise TypeError('Expected value as ValueANU2 or ValueVOS2, \
                    ValueVOS4 or ValueCUS4 got {}'.format(type(values[x])))

        cmd = Cmd(self.com)
        return cmd.getIoGroup(channels, values)
    
    
    def getParamValue(self, channel, value):
        """Get the Configuration Parameter "Value" of an analog input channel.
            
        This method calls the GetParam function of the module and returns
            the value of the Configuration Parameter "Value".
        
            The Configuration Parameter "Value" contains the current
            value of the input channel.
        
        It is recommended to call getIo instead of this method.
        
        Args:
            channel: IO channel number. Must be in valid range
            value: Value object of ValueANU2 class
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        if not isinstance (channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))

        if not isinstance(value, ValueANU2):
            raise TypeError('Expected value as ValueANU2, got {}'.format(
                type(value)))

        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCAIParamAddress.VALUE, channel, data)
        
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            value.setData(data)
        return ret

    def getParamMode(self, channel, mode):
        """Get the Configuration Parameter "Mode" of the analog input channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number. Must be in the valid range
            mode: Operation Mode as a list with one LCAIMode integer value
            
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

        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')     

        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCAIParamAddress.MODE, channel, data)

        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            if data[0] == LCAIMode.INACTIVE:
                mode = LCAIMode.INACTIVE
            elif data[0] == LCAIMode.STANDARD:
                mode[0] = LCAIMode.STANDARD
            else:
                mode[0] = LCAIMode.INACTIVE
        return ret

    def setParamModeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Mode" of an analog input channel
            to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Mode" to the default value.
        
        Args:
            channel: IO channel number. Must be in the valid range
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
        return cmd.setParamDefault(_LCAIParamAddress.MODE, channel, persistent)

    def setParamMode(self, channel, persistent, mode):
        """Set the Configuration Parameter "Mode" of an analog input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number. Must be in the valid range
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCAI4Mode integer value
        
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

        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')

        data = bytearray([mode])
        cmd = Cmd(self.com)
        return cmd.setParam(_LCAIParamAddress.MODE, channel, persistent, data)

    def setParamFlagsDefault(self, channel, persistent):
        """Set the Configuration Parameter "Flags" of an analog input to the
            default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Flags" to the default value.
        
        Args:
            channel: IO channel number. Must be in the valid range
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
        return cmd.setParamDefault(_LCAIParamAddress.FLAGS, channel, persistent)

    def getParamNrSamples(self, channel, nrSamples):
        """Get the Configuration Parameter "Number of Samples" of the analog input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Number of Samples".
          
        Args:
            channel: IO channel number. Must be in the valid range
            nrSamples: Number of Samples as a list containing one integer value
                in milliseconds
            
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
        
        if not isinstance(nrSamples, list):
            raise TypeError('Expected nrSamples as list, got {}'.format(
                type(nrSamples)))
        
        if len(nrSamples) < 1:
            raise TypeError('Expected nrSamples as list with 1 int, got {}'.format(
                len(nrSamples)))
        
        if not isinstance(nrSamples[0], int):
            raise TypeError('Expected nrSamples[0] as int, got {}'.format(
                type(nrSamples[0])))
            
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCAIParamAddress.NR_SAMPLES, channel, data)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            nrSamples[0] = struct.unpack("<H", data)[0]
        else:
            nrSamples[0] = 0
        return ret

    def setParamNrSamplesDefault(self, channel, persistent):
        """Set the Configuration Parameter "Number of Samples" of an analog
            input to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Number of Samples" to the default value.
        
        Args:
            channel: IO channel number. Must be in the valid range
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
        return cmd.setParamDefault(_LCAIParamAddress.NR_SAMPLES, channel,
            persistent)

    def setParamNrSamples(self, channel, persistent, nrSamples):
        """Set the Configuration Parameter "Number of Samples" of an analog
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Number of Samples".
        
        Args:
            channel: IO channel number. Must be in the valid range
            persistent: Store parameter permanently if true
            nrSamples: Parameter "Number of Samples"
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or nrSamples value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(nrSamples, int):
            raise TypeError('Expected nrSamples as int, got {}'.format(
                type(nrSamples)))
        
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')
        
        if (nrSamples < 0):
            raise ValueError('nrSamples out of range')

        data = bytearray(struct.pack("<H", nrSamples))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCAIParamAddress.NR_SAMPLES, channel,
            persistent, data)  

    
    def getParamOffset(self, channel, offset):
        """Get the Configuration Parameter "Offset" of the analog input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Offset".
          
        Args:
            channel: IO channel number. Must be in the valid range
            offset: Offset as a list containing one integer value
            
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
            
        if not isinstance(offset, list):
            raise TypeError('Expected offset as list, got {}'.format(
                type(offset)))
        
        if len(offset) < 1:
            raise TypeError('Expected offset as list with 1 int, got {}'.format(
                len(offset)))
        
        if not isinstance(offset[0], int):
            raise TypeError('Expected offset[0] as int, got {}'.format(
                type(offset[0])))
            
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')     
        
        data = bytearray()
        cmd = Cmd(self.com)
        ret = cmd.getParam(_LCAIParamAddress.OFFSET, channel, data)
    
        if ret == IoReturn.IoReturn.IO_RETURN_OK:
            offset[0] = struct.unpack("<h", data)[0]
        else:
            offset[0] = 0
        return ret

    def setParamOffsetDefault(self, channel, persistent):
        """Set the Configuration Parameter "Offset" of an analog input channel to the
            default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Offset" to the default value.
        
        Args:
            channel: IO channel number. Must be in the valid range
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
        return cmd.setParamDefault(_LCAIParamAddress.OFFSET, channel, persistent)

    def setParamOffset(self, channel, persistent, offset):
        """Set the Configuration Parameter "Offset" of an analog
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Offset".
        
        Args:
            channel: IO channel number. Must be in the valid range
            persistent: Store parameter permanently if true
            offset: Parameter "Offset" 
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or offset value is out of range
        """
        if not isinstance(channel, int):
            raise TypeError('Expected channel as int, got {}'.format(
                type(channel)))
        
        if not isinstance(persistent, bool):
            raise TypeError('Expected persistent as bool, got {}'.format(
                type(persistent)))
        
        if not isinstance(offset, int):
            raise TypeError('Expected offset as int, got {}'.format(
                type(offset)))
        
        if (channel >= self.nrOfChannels):
            raise ValueError('Channel out of range')
        
        if (offset < (-pow(2, 15))) | (offset >= pow(2, 16)):
            raise ValueError('Offset out of range')

        data = bytearray(struct.pack("<h", offset))
        cmd = Cmd(self.com)
        return cmd.setParam(_LCAIParamAddress.OFFSET, channel, persistent,
            data) 

    def getDeviceTypeName(self):
        """Get device type name as string.
        
        Returns:
            String of the device type name
        
        Raises:
            ValueError: ID data not valid
        """
        if self.id.validData == True:
            if (self.id.deviceType == LCAIDeviceType.AI_0_5[0]):
                return LCAIDeviceType.AI_0_5[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_10[0]):
                return LCAIDeviceType.AI_0_10[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_12[0]):
                return LCAIDeviceType.AI_0_12[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_15[0]):
                return LCAIDeviceType.AI_0_15[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_20[0]):
                return LCAIDeviceType.AI_0_20[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_24[0]):
                return LCAIDeviceType.AI_0_24[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_5_5[0]):
                return LCAIDeviceType.AI_5_5[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_10_10[0]):
                return LCAIDeviceType.AI_10_10[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_12_12[0]):
                return LCAIDeviceType.AI_12_12[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_15_15[0]):
                return LCAIDeviceType.AI_15_15[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_20_20[0]):
                return LCAIDeviceType.AI_20_20[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_24_24[0]):
                return LCAIDeviceType.AI_24_24[1]
            elif (self.id.deviceType == LCAIDeviceType.AI_0_20MA_500[0]):
                return LCAIDeviceType.AI_0_20MA_500[1]
            else:
                return "Not Identified"

    def getDeviceType(self):
        """Get device type.
        
        Returns:
            Device type
        """
        if (self.id.validData == True):
            return self.id.deviceType
        else:
            return LCAIDeviceType.AI_NONE

    def __init__(self, portName):
        """
        Constructor of LucidControl Analog Input USB Module class
        """
        LucidControl.__init__(self, portName)
        self.nrOfChannels = 0