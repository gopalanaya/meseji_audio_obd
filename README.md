# meseji_audio_obd
An application to run Audio OBD Campaign

# Installation guideline.
if you face migration error, login to postgresql or db shell and run below command
ALTER TABLE smartping_voxupload ADD CONSTRAINT voiceid_unique_id UNIQUE(voiceid);
