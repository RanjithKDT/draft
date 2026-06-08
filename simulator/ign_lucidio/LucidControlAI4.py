'''
Created on 14.06.2013
LucidControl Analog Input USB Module AI4 implementation
@author: Klaus Ummenhofer
'''

from lucidIo.LucidControlAI import LucidControlAI

    
class LucidControlAI4(LucidControlAI):
    """ LucidControl Analog Input USB Module AI4 class
    """
    
    def getIo(self, channel, value):
        """Get the value or state of an analog input channel.
            
        This method calls the GetIo function of the module and returns
        the value or of the analog input channel.
        
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
        """Get the values of a group of analog input channels.
            
        This method calls the GetIoGroup function of the module and
            returns the values of a group of analog input channels.
        
        Args:
            channels: Tuple with 4 boolean values (one for each channel).
                A channel is only read if the corresponding channel is
                true.
            values: Value objects
                A tuple with 4 value objects. The value objects must be
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
    
    
    def getParamValue(self, channel, value):
        """Get the Configuration Parameter "Value" of an analog input channel.
            
        This method calls the GetParam function of the module and returns
            the value of the Configuration Parameter "Value".
        
            The Configuration Parameter "Value" contains the current
            value of the input channel.
        
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
        """Get the Configuration Parameter "Mode" of the analog input channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            mode: Operation Mode as a list with one LCAIMode integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamMode(channel, mode)


    def setParamModeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Mode" of an analog input channel
            to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Mode" to the default value.
        
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

        return super().setParamModeDefault(channel, persistent)

    def setParamMode(self, channel, persistent, mode):
        """Set the Configuration Parameter "Mode" of an analog input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCAIMode integer value
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range    
        """
        return super().setParamMode(channel, persistent, mode)

    
    def setParamFlagsDefault(self, channel, persistent):
        """Set the Configuration Parameter "Flags" of an analog input to the
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
        return super().setParamFlagsDefault(channel, persistent)

        
    def getParamNrSamples(self, channel, nrSamples):
        """Get the Configuration Parameter "Number of Samples" of the analog input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Number of Samples".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            nrSamples: Number of Samples as a list containing one integer value
                in milliseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """        
        return super().getParamNrSamples(channel, nrSamples)


    
    def setParamNrSamplesDefault(self, channel, persistent):
        """Set the Configuration Parameter "Number of Samples" of an analog
            input to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Number of Samples" to the default value.
        
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
        return super().setParamNrSamplesDefault(channel, persistent)


    def setParamNrSamples(self, channel, persistent, nrSamples):
        """Set the Configuration Parameter "Number of Samples" of an analog
            input channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Number of Samples".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            persistent: Store parameter permanently if true
            nrSamples: Parameter "Number of Samples"
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or nrSamples value is out of range
        """

        return super().setParamNrSamples(channel, persistent, nrSamples)
    
    
    def getParamOffset(self, channel, offset):
        """Get the Configuration Parameter "Offset" of the analog input
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Offset".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 3
            offset: Offset as a list containing one integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """        
        return super().getParamOffset(channel, offset)

    
    def setParamOffsetDefault(self, channel, persistent):
        """Set the Configuration Parameter "Offset" of an analog input to the
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
            input channel.
            
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
        Constructor of LucidControl Analog Input USB Module class
        """
        LucidControlAI.__init__(self, portName)
        self.nrOfChannels = 4
        