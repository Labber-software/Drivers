//	Include file for Vaunix Lab Brick Frequency Synthesizers
//
//	1/18/2009	RD	Fixed values of DevStatus bit masks.	
// 
//	1/23/2009	RD	Added new function for Minimum Power
//	3/4/2009	RD	Added declaration for fnLSG_GetDeviceStatus



#define VNX_FSYNSTH_API __declspec(dllimport)


// ----------- Global Equates ------------
#define MAXDEVICES 64
#define MAX_MODELNAME 32

// ----------- Data Types ----------------

#define DEVID unsigned int


// ----------- Mode Bit Masks ------------

#define MODE_RFON	0x00000010			// bit is 1 for RF on, 0 if RF is off
#define MODE_INTREF	0x00000020			// bit is 1 for internal osc., 0 for external reference
#define MODE_SWEEP	0x0000000F			// bottom 4 bits are used to keep the sweep control bits				


// ----------- Command Equates -----------


// Status returns for commands
#define LVSTATUS int

#define STATUS_OK 0
#define BAD_PARAMETER 0x80010000		// out of range input -- frequency outside min/max etc.
#define BAD_HID_IO    0x80020000		// a failure occurred internally during I/O to the device
#define DEVICE_NOT_READY 0x80030000		// device isn't open, no handle, etc.

// Status returns for DevStatus

#define INVALID_DEVID 0x80000000		// MSB is set if the device ID is invalid
#define DEV_CONNECTED 0x00000001		// LSB is set if a device is connected
#define DEV_OPENED	  0x00000002		// set if the device is opened
#define SWP_ACTIVE	  0x00000004		// set if the device is sweeping
#define SWP_UP		  0x00000008		// set if the device is sweeping up in frequency
#define SWP_REPEAT	  0x00000010		// set if the device is in continuous sweep mode

// Internal values in DevStatus
#define DEV_LOCKED	  0x00000020		// used internally by the dll
#define DEV_RDTHREAD  0x00000040


VNX_FSYNSTH_API void fnLSG_SetTestMode(bool testmode);
VNX_FSYNSTH_API int fnLSG_GetNumDevices();
VNX_FSYNSTH_API int fnLSG_GetDevInfo(DEVID *ActiveDevices);
VNX_FSYNSTH_API int fnLSG_GetModelName(DEVID deviceID, char *ModelName);
VNX_FSYNSTH_API int fnLSG_InitDevice(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_CloseDevice(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetSerialNumber(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetDeviceStatus(DEVID deviceID);


VNX_FSYNSTH_API LVSTATUS fnLSG_SetFrequency(DEVID deviceID, int frequency);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetStartFrequency(DEVID deviceID, int startfrequency);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetEndFrequency(DEVID deviceID, int endfrequency);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetFrequencyStep(DEVID deviceID, int frequencystep);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetDwellTime(DEVID deviceID, int dwelltime);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetPowerLevel(DEVID deviceID, int powerlevel);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetRFOn(DEVID deviceID, bool on);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetUseInternalRef(DEVID deviceID, bool internal);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetSweepDirection(DEVID deviceID, bool up);
VNX_FSYNSTH_API LVSTATUS fnLSG_SetSweepMode(DEVID deviceID, bool mode);
VNX_FSYNSTH_API LVSTATUS fnLSG_StartSweep(DEVID deviceID, bool go);
VNX_FSYNSTH_API LVSTATUS fnLSG_SaveSettings(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetFrequency(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetStartFrequency(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetEndFrequency(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetDwellTime(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetFrequencyStep(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetRF_On(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetUseInternalRef(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetPowerLevel(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetMaxPwr(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetMinPwr(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetMaxFreq(DEVID deviceID);
VNX_FSYNSTH_API int fnLSG_GetMinFreq(DEVID deviceID);

