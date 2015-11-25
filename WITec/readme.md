#WITec Control FOUR remote

##Prerequisite

This driver uses the COM-interface of the WITec Control FOUR software. This interface has to be enabled first or the driver will not work at all. (Please refer to the WITec manuals for this.)

##General notes
- The auto-close function closes any WITec-window which has not been open when the function has been activated. Therefore, enable the remote in the WITec software before activating this channel.
- For automatical naming add an auto-name channel as a step channel and enable channel relations to set it to the same value as the main loop. You can then use the number of the auto-name channel as a placeholder in the naming following the Python "format" function. (For example, use {0} as a placeholder for the first auto-name channel)
- A measurement is triggered by reading one of the trigger-channels.
- "TriggerAndReadSingleSpectrum" can retrieve the data of a single spectrum into Labber. This is done by telling WITec to save the current project to the HDD and then read the latest spectrum from this file. For this to work, you have to change some setting in "Auto Save": Make sure, that the file is saved using the "extra directory" and that WITec is set to override files. The driver will change the output to C:\Labber-Temp by itself. It is also highly recommended to "Store and clear" to speed up this process. Unfortunately, with this method you will have your data in Labber only.
