from ffmpeg import FFmpeg, Progress
import json
import os
from pathlib import Path


def construct_output_filename(inputfile):
    """ This function is intended to get the output filename that will be used for
    Audio translation.
    Initial Requirement: inputfile should be audio file only,
    it can be audio/wav, audio/mp3, etc
    """
    inputfile_name = os.path.basename(inputfile)
    # Make sure that output file should be .wav,
    if not inputfile_name.endswith('.wav'):
        # filename can have multiple dots and name should be 10 chars only
        inputfile_name = "_".join(inputfile_name.split('.')[:-1])[:10] + '.wav' 
        
    dirname = os.path.dirname(inputfile)
    outputfile_name = os.path.join(dirname, 'p_'+ inputfile_name)

    return outputfile_name


def read_audio_meta(inputfile):
    """ This function will read the audio Meta data and return dict of result
    """
    ffmpeg = FFmpeg(executable='ffprobe').input(inputfile, print_format="json", show_streams=None)
    media = json.loads(ffmpeg.execute())

    for m in media['streams']:
        if m['codec_type'] == 'audio':
            result = {
                'sample_rate': m['sample_rate'],
                'channels': m['channels'],
                'bits_per_sample': m['bits_per_sample'],
                'duration': m['duration'],
            }

    return result


def verify_audio_file(inputfile):
    """ This function will verify that input file is of type audio or not
      inputfile: Any path containing audio file 

      output:  {
          'result': 'OK' | 'Failed',
          'target': {'channels': 'mono', 'sample_rate': '8000', 'bits_per_sample': '8'},
          'input': {'channel': 'channel', 'frequency': 'frequency', 'bit': }
      }

    """
    result = {'target': {
                'sample_rate': "8000",
                'channels': 1,
                'bits_per_sample': 8,
                'duration': '30',
    }
    }

    result['input'] = read_audio_meta(inputfile)
    
    # We assume all bits matched
    result['result'] = 'OK'
    for params in ['sample_rate', 'channels', 'bits_per_sample']:
        if result['target'].get(params) != result['input'].get(params):
            result['result'] = 'Failed'

    
    return result


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
            {'ar': '8000', 'ac': 1, 's': 8, 'acodec':'pcm_u8'}
            )
    )

    @ffmpeg.on('progress')
    def on_progress(progress: Progress):
        print(progress)

    
    ffmpeg.execute()








            
            


    