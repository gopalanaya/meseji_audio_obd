from ffmpeg import FFmpeg, Progress
import  os
from pathlib import Path

def construct_output_filename(inputfile):
    """ This function is intended to get the output filename that will be used for
    Audio translation.
    Initial Requirement: inputfile should be audio file only,
    it can be audio/wav, audio/mp3, etc
    """
    inputfile_name = os.path.basename(inputfile)
    # Make sure that output file should be .wav,
    if not inputfile_name.endswith('.mp3'):
        # filename can have multiple dots
        inputfile_name = "".join(inputfile_name.split('.')[:-1]) + '.mp3' 
        
    dirname = os.path.dirname(inputfile)
    outputfile_name = os.path.join(dirname, 'processed'+ inputfile_name)

    return outputfile_name


def convert_audio_file(inputfile):
    """ This will convert the given audio file to required format 8bit mono 8000hz file
    Generate the dynamic
    """
    outputfile_name = construct_output_filename(inputfile)
    # Get absolute path
    inputfile = Path(inputfile)
    outputfile_name = Path(outputfile_name)
    ffmpeg = (
        FFmpeg()
        .option('y')
        .input(inputfile)
        .output(
            outputfile_name,
            {'ab': '128k', 'ac': 1, 'acodec':'libmp3lame'}
            )
    )

    @ffmpeg.on('progress')
    def on_progress(progress: Progress):
        print(progress)

    
    ffmpeg.execute()
