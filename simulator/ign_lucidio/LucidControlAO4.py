'''
Created on 08.04.2023
LucidControl Analog Output USB Module AO4 implementation
@author: Klaus Ummenhofer
'''
from lucidIo.LucidControlAO import LucidControlAO
from lucidIo import IoReturn


class LucidControlAO4(LucidControlAO):
    """""LucidControl Analog Output USB Module AO4 class
    """
    
    def getIo(self, channel, value):
        """Get the value or state of an analog output channel.
            
        This method calls the GetIo function of the module and returns
        the current value or of the analog output channel.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            value: Value object. Must be either ValueVOS4, ValueVOS2,
                ValueCUS4 or ValueANU2
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getIo(channel, value)
  


    def getIoGroup(self, channels, values):
        """Get the values of a group of analog output channels.
            
        This method calls the GetIoGroup function of the module and
            returns the current values of a group of analog output channels.
        
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only read if the corresponding channel is
                true.
            values: Value objects
                A tuple with 8 value objects. The value objects must be
                either ValueVOS4, ValueVOS2, ValueCUS4 or ValueANU2.
                The function fills the objects with read data.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getIoGroup(channels, values)
    
    
    def setIo(self, channel, value):
        """Write the value of one analog output channel.
        
        This method calls the SetIo function of the module and writes
            the value of the analog output channel.
            
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            value: Value object. Must be either ValueVOS4, ValueVOS2,
                ValueCUS4 or ValueANU2
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setIo(channel, value)
    


    def setIoGroup(self, channels, values):
        """Write values of a group of analog output channels.
        
        This method calls the SetIoGroup function of the module and
            writes the values of a group of analog output channels.
            
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only written if the corresponding channel is
                true.
            values: A tuple with 8 value objects.
                The value objects must be either ValueVOS4, ValueVOS2,
                ValueCUS4 or ValueANU2.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setIoGroup(channels, values)

    
    
    def getParamValue(self, channel, value):
        """Get the Configuration Parameter "Value" of an analog output channel.
            
        This method calls the GetParam function of the module and returns
            the value of the Configuration Parameter "Value".
        
            The Configuration Parameter "Value" contains the current
            value of the analog output channel.
        
        It is recommended to call getIo instead of this method.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            value: Value object of ValueANU2 class
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamValue(channel, value)


    
    def getParamMode(self, channel, mode):
        """Get the Configuration Parameter "Mode" of the analog output channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            mode: Operation Mode as a list with one LCAOMode integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamMode(channel, mode)


    def setParamModeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Mode" of an analog output channel
            to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Mode" to the default value.
        
        Args:
            channel: IO channel number. Must be the range 0 ... 3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamModeDefault(channel, persistent)

    
    def setParamMode(self, channel, persistent, mode):
        """Set the Configuration Parameter "Mode" of an analog output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCAOMode integer value
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range    
        """
        return super().setParamMode(channel, persistent, mode)

    
    def setParamFlagsDefault(self, channel, persistent):
        """Set the Configuration Parameter "Flags" of an analog output to the
            default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Flags" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamMode(channel, persistent)



    def getParamRefreshTime(self, channel, refreshTime):
        """Get the Configuration Parameter "Refresh Time" of the analog output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Refresh Time".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            refreshTime: Refresh Time as a list containing one integer value
                in microseconds.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """      
        return super().getParamRefreshTime(channel, refreshTime)


    
    def setParamRefreshTimeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Refresh Time" of an analog
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Refresh Time" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamRefreshTime(channel, persistent)


    def setParamRefreshTime(self, channel, persistent, refreshTime):
        """Set the Configuration Parameter "Refresh Time" of an analog
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Refresh Time".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            refreshTime: Parameter "Refresh Time" in microseconds.
                Value must be positive.
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or setupTime value is out of range
        """
        return super().setParamRefreshTime(channel, persistent, refreshTime)

    
    def getParamOffset(self, channel, offset):
        """Get the Configuration Parameter "Offset" of the analog output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Offset".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            offset: Offset as a list containing one integer value
                representing the offset voltage in millivolt.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamOffset(channel, offset)

    
    def setParamOffsetDefault(self, channel, persistent):
        """Set the Configuration Parameter "Offset" of an analog output to the
            default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Offset" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamOffsetDefault(channel, persistent)
    
    
    def setParamOffset(self, channel, persistent, offset):
        """Set the Configuration Parameter "Offset" of an analog
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Offset".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            offset: Parameter "Offset" 
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or offset value is out of range
        """
        return super().setParamOffset(channel, persistent, offset)
 
            
    def __init__(self, portName):
        """
        Constructor of LucidControl Analog Output USB Module class
        """
        LucidControlAO.__init__(self, portName)
        self.nrOfChannels = 4
        