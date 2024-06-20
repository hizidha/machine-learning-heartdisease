import os
import numpy as np
import noisereduce as nr
from scipy.io import wavfile
from datetime import datetime
from pydub import AudioSegment
from keras.models import load_model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH_LSTM = os.path.join(BASE_DIR, 'lst_10_1.h5')
MODEL_PATH_GRU = os.path.join(BASE_DIR, 'gru_10_1.h5')
MODEL_PATH_TCN = os.path.join(BASE_DIR, 'tcn_10_1.h5')

# Global variables to store the loaded models
model_lstm = None
model_gru = None
model_tcn = None

def load_models():
    global model_lstm, model_gru, model_tcn
    model_lstm = load_model(MODEL_PATH_LSTM)
    model_gru = load_model(MODEL_PATH_GRU)
    model_tcn = load_model(MODEL_PATH_TCN)

# Call the function to load the models
load_models()

def preprocessAudio(wav_file_path):
    SEGMENT_LENGTH_MS = 15000  # 15 seconds
    TEMP_SEGMENTED_PATH = "temp_segmented.wav"
    OUTPUT_FOLDER = "data/"

    try:
        # Load and segment the audio file
        audio = AudioSegment.from_wav(wav_file_path)
        if len(audio) < SEGMENT_LENGTH_MS:
            looped_audio = audio
            while len(looped_audio) < SEGMENT_LENGTH_MS:
                looped_audio += audio
            segmented_audio = looped_audio[:SEGMENT_LENGTH_MS]
        else:
            segmented_audio = audio[:SEGMENT_LENGTH_MS]
        
        # Export the segmented audio to a temporary file
        segmented_audio.export(TEMP_SEGMENTED_PATH, format="wav")
        
        # Denoise the audio
        rate, data = wavfile.read(TEMP_SEGMENTED_PATH)
        reduced_noise = nr.reduce_noise(y=data, sr=rate, time_mask_smooth_ms=128)
        
        # Normalize and FFT the audio data
        max_val = np.max(np.abs(reduced_noise))
        if max_val == 0:
            raise ValueError("The maximum value of the audio data is 0, normalization failed.")
        normalized_data = reduced_noise / max_val
        fft_data = np.abs(np.fft.fft(normalized_data))
        
        # Save the FFT data to a file
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
        unique_filename = datetime.now().strftime('%y-%m-%d_%H~%M~%S') + ".npy"
        output_file_path = os.path.join(OUTPUT_FOLDER, unique_filename)
        np.save(output_file_path, fft_data)
        print(f"FFT data shape: {fft_data.shape}")
        
        # Reshape the FFT data
        reshaped_fft_data = fft_data.reshape(1, 1, fft_data.shape[0])
        
        print("Your Preprocessing Data is Completed")
        
        return reshaped_fft_data
    
    except FileNotFoundError:
        print(f"Error: File {wav_file_path} not found.")
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure the temporary segmented file is removed
        if os.path.exists(TEMP_SEGMENTED_PATH):
            os.remove(TEMP_SEGMENTED_PATH)

    return None

def callMymodel(wav_file_path):
    preprocessed_data = preprocessAudio(wav_file_path)
    
    if preprocessed_data is not None:
        # Load the models
        global model_lstm, model_gru, model_tcn
        
        # Predict using the models
        prediction_lstm = model_lstm.predict(preprocessed_data)
        prediction_gru = model_gru.predict(preprocessed_data)
        prediction_tcn = model_tcn.predict(preprocessed_data)
        
        weights = [1, 1, 1]
        
        ttl_weight = sum(weights)
        lst_weight = weights[0] / ttl_weight
        gru_weight = weights[1] / ttl_weight
        tcn_weight = weights[2] / ttl_weight
        
        ensemble_pred = (prediction_lstm * lst_weight + 
                         prediction_gru * gru_weight + 
                         prediction_tcn * tcn_weight)
    
        y_pred = (ensemble_pred > 0.5).astype(int)
        
        # Determine the prediction result
        preds = "abnormal" if y_pred[0] == 1 else "normal"
        return preds
    
    return None
