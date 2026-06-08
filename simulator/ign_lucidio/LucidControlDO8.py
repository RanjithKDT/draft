"""
LucidControl Digital Output USB Module DO8 implementation
@author: Klaus Ummenhofer
"""

from lucidIo.LucidControlDO import LucidControlDO

class LucidControlDO8(LucidControlDO):
    """LucidControl Digital Output USB Module DO8 class
    """
    
    def getIo(self, channel, value):
        """Get the value or state of one digital output channel.
            
        This method calls the GetIo function of the module and returns
        the value or state of the digital output channel.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            value: Digital value object of type ValueDI1.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getIo(channel, value)
        

    def getIoGroup(self, channels, values):
        """Get the values or states of a group of digital output
            channels.
            
        This method calls the GetIoGroup function of the module and
            returns the values or states of a group of output channels.
        
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only read if the corresponding channel is
                true.
            values: Digital values.
                A tuple with 8 digital value objects. The function fills
                the objects with read data.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getIoGroup(channels, values)
 
   
    def setIo(self, channel, value):
        """Write the value or state of one digital output channel.
        
        This method calls the SetIo function of the module and writes
            the value or state of the digital output channel.
            
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            value: Digital value object of type ValueDI1, initialized
                with the updated data.
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setIo(channel, value)


    def setIoGroup(self, channels, values):
        """Write values or states of a group of output channels.
        
        This method calls the SetIoGroup function of the module and
            writes the values or states of a group of output channels.
            
        Args:
            channels: Tuple with 8 boolean values (one for each channel).
                A channel is only written if the corresponding channel is
                true.
            values: Digital values.
                A tuple with 8 digital value objects. The values of the
                objects are written to the output channels.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setIoGroup(channels, values)
    
    
    def getParamValue(self, channel, value):
        """Get the Configuration Parameter "Value" of a digital
            output channel.
            
        This method calls the GetParam function of the module and returns
        the value of the Configuration Parameter "Value".
        
        The Configuration Parameter "Value" contains the current value
        or state of the output channel.
        
        It is recommended to call getIo instead of this method.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            value: Digital value object of type ValueDI1.
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamValue(channel, value)

    
    def setParamValueDefault(self, channel, persistent):
        """Set the Configuration Parameter "Value" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Value" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamValueDefault(channel, persistent)

    
    def setParamValue(self, channel, persistent, value):
        return super().setParamValue(channel, persistent, value)

    
    def getParamMode(self, channel, mode):
        """Get the Configuration Parameter "Mode" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Mode".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            mode: Operation Mode as a list with one LCDOMode integer value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamMode(channel, mode)
        

    def setParamModeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Mode" of a digital
            output channel to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Mode" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
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
        """Set the Configuration Parameter "Mode" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Mode".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            mode: Operation Mode as LCDOMode integer value
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range    
        """
        return super().setParamMode(channel, persistent, mode)


    def setParamFlagsDefault(self, channel, persistent):
        """Set the Configuration Parameter "Flags" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Flags" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamFlagsDefault(channel, persistent)

    
    def getParamFlagCanCancel(self, channel, canCancel):
        """Get the Configuration Parameter Flag "Can Cancel".
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Can Cancel".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            canCancel: Parameter Flag "Can Cancel" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamFlagCanCancel(channel, canCancel)
        
    
    def setParamFlagCanCancel(self, channel, persistent, canCancel):
        """Set the Configuration Parameter Flag "Can Cancel".
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Can Cancel".
        
         Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            canCancel: Parameter Flag "Can Cancel" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamFlagCanCancel(channel, persistent, canCancel)
        
    
    def getParamFlagCanRetrigger(self, channel, canRetrigger):
        """Get the Configuration Parameter Flag "Can Retrigger".
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Can Retrigger".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            canRetrigger: Parameter Flag "Can Retrigger" as a list containing
                one boolean value
                
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamFlagCanRetrigger(channel, canRetrigger)

    
    def setParamFlagCanRetrigger(self, channel, persistent, canRetrigger):
        """Set the Configuration Parameter Flag "Can Retrigger".
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Can Retrigger".
        
         Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            canRetrigger: Parameter Flag "Can Retrigger" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamFlagCanRetrigger(channel, persistent, canRetrigger)
    
    
    def getParamFlagInverted(self, channel, inverted):
        """Get the Configuration Parameter Flag "Inverted".
        
        This method calls the GetParam function of the module and
        returns the Configuration Flag "Inverted".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            inverted: Parameter Flag "Inverted" as a list containing
                one boolean value
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamFlagInverted(channel, inverted)
 
    
    def setParamFlagInverted(self, channel, persistent, inverted):
        """Set the Configuration Parameter Flag "Inverted".
        
        This method calls the SetParam function of the module and
        sets the Configuration Flag "Inverted".
        
         Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            inverted: Parameter Flag "Inverted" as boolean
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamFlagInverted(channel, persistent, inverted)

    
    def getParamCycleTime(self, channel, cycleTime):
        """Get the Configuration Parameter "Cycle Time" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Cycle Time".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            cycleTime: Parameter "Cycle Time" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamCycleTime(channel, cycleTime)
        
    
    def setParamCycleTimeDefault(self, channel, persistent):
        """Set the Configuration Parameter "Cycle Time" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Cycle Time" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamCycleTimeDefault(channel, persistent)

    
    def setParamCycleTime(self, channel, persistent, cycleTime):
        """Set the Configuration Parameter "Cycle Time" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Cycle Time".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            cycleTime: Parameter "Cycle Time" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or cycleTime value is out of range
        """
        return super().setParamCycleTime(channel, persistent, cycleTime)

    
    def getParamDutyCycle(self, channel, dutyCycle):
        """Get the Configuration Parameter "Duty Cycle" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "Duty Cycle".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            dutyCycle: Parameter "Duty Cycle" as a list containing one integer
                value  (Duty Cycle as 1/1000)
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamDutyCycle(channel, dutyCycle)
        
    
    def setParamDutyCycleDefault(self, channel, persistent):
        """Set the Configuration Parameter "Duty Cycle" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "Duty Cycle" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamDutyCycleDefault(channel, persistent)

    
    def setParamDutyCycle(self, channel, persistent, dutyCycle):
        """Set the Configuration Parameter "Duty Cycle" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "Duty Cycle".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            dutyCycle: Parameter "Duty Cycle" in 1/1000
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or dutyCycle value is out of range
        """
        return super().setParamDutyCycle(channel, persistent, dutyCycle)
    
    
    def getParamOnHold(self, channel, onHold):
        """Get the Configuration Parameter "On Hold" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "On Hold".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            onHold: Parameter "On Hold" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamOnHold(channel, onHold)


    def setParamOnHoldDefault(self, channel, persistent):
        """Set the Configuration Parameter "On Hold" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "On Hold" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamOnHoldDefault(channel, persistent)
    
    
    def setParamOnHold(self, channel, persistent, onHold):
        """Set the Configuration Parameter "On Hold" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "On Hold".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            onHold: Parameter "On Hold" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or onHold value is out of range
        """
        return super().setParamOnHold(channel, persistent, onHold)
    
    
    def getParamOnDelay(self, channel, onDelay):
        """Get the Configuration Parameter "On Delay" of the digital output
            channel.
            
        This method calls the GetParam function of the module and returns
            the Configuration Parameter "On Delay".
          
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            onDelay: Parameter "On Delay" as a list containing one integer
                value in microseconds
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().getParamOnDelay(channel, onDelay)


    def setParamOnDelayDefault(self, channel, persistent):
        """Set the Configuration Parameter "On Delay" of a digital
            output to the default value.
            
        This method calls the SetParam function of the module and sets
        the Configuration Parameter "On Delay" to the default value.
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel value is out of range
        """
        return super().setParamOnDelayDefault(channel, persistent)

    
    def setParamOnDelay(self, channel, persistent, onDelay):
        """Set the Configuration Parameter "On Delay" of a digital
            output channel.
            
        This method calls the SetParam function of the module and sets the
        Configuration Parameter "On Delay".
        
        Args:
            channel: IO channel number. Must be in the range 0 ... 7
            persistent: Store parameter permanently if true
            onDelay: Parameter "On Delay" in microseconds
        
        Returns:
            IO_RETURN_OK in case of success, otherwise detailed IoReturn
            error code.
        
        Raises:
            TypeError: Passed argument types are wrong
            ValueError: Channel or onDelay value is out of range
        """
        return super().setParamOnDelay(channel, persistent, onDelay)

    
    def getDeviceTypeName(self):
        """Get device type name as string.
        
        Returns:
            String of the device type name
        
        Raises:
            ValueError: ID data not valid
        """
        return super().getDeviceTypeName()
    
    
    def getDeviceType(self):
        """Get device type.
        
        Returns:
            Device type
        """
        return super().getDeviceType()

    
    def __init__(self, portName):
        """
        Constructor of LucidControl Digital Output USB Module class
        """
        LucidControlDO.__init__(self, portName)
        self.nrOfChannels = 8
        
        