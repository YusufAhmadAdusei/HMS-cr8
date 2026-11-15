import torch
import torchaudio
import torch.nn.functional as F

from pathlib import Path


class AstraStressPredictor:

    def __init__(self):

        try:
            from transformers import (
                AutoConfig,
                AutoModelForAudioClassification,
            )
        except ImportError as exc:
            raise ImportError(
                "The stress predictor requires transformers. "
                "Install project dependencies with "
                "`python -m pip install -r requirements.txt`."
            ) from exc

        self.repo = "forwarder1121/voice-based-stress-recognition"
        self.cache_dir = Path(__file__).resolve().parents[1] / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print("Loading ASTRA Stress AI...")
        print("Device:", self.device)

        # Load custom Hugging Face classifier.
        # Pinning a repository revision makes the code reproducible.
        self.revision = "93fbf3bc114f41e502b9642ce6e7e17f970075bd"

        self.config = AutoConfig.from_pretrained(
            self.repo,
            trust_remote_code=True,
            revision=self.revision,
            cache_dir=self.cache_dir,
        )

        self.stress_model = AutoModelForAudioClassification.from_pretrained(
            self.repo,
            trust_remote_code=True,
            revision=self.revision,
            cache_dir=self.cache_dir,
        )

        self.stress_model.to(self.device)
        self.stress_model.eval()

        # Load Wav2Vec2 BASE encoder.
        bundle = torchaudio.pipelines.WAV2VEC2_BASE

        self.wav2vec = bundle.get_model(
            dl_kwargs={"model_dir": str(self.cache_dir)}
        ).to(self.device)
        self.wav2vec.eval()

        self.target_sample_rate = 16000

        print("ASTRA Stress AI loaded successfully.")

    def load_audio(self, audio_path):

        waveform, sample_rate = torchaudio.load(
            str(audio_path)
        )

        # Convert stereo to mono.
        waveform = waveform.mean(dim=0, keepdim=True)

        # Resample to 16 kHz.
        if sample_rate != self.target_sample_rate:

            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=self.target_sample_rate
            )

            waveform = resampler(waveform)

        return waveform

    def extract_embedding(self, waveform):

        waveform = waveform.to(self.device)

        with torch.inference_mode():

            features = self.wav2vec(waveform)[0]

            # Temporal mean pooling.
            embedding = features.mean(dim=1)

            # Match the 512-dimensional input expected by StudentNet.
            embedding = embedding[:, :512]

        return embedding

    def predict(self, audio_path):

        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        waveform = self.load_audio(audio_path)

        if waveform.shape[1] < 16000:
            raise ValueError(
                "Audio must contain at least one second of speech."
            )

        embedding = self.extract_embedding(waveform)

        with torch.inference_mode():

            outputs = self.stress_model(
                embedding
            )

            probabilities = F.softmax(
                outputs.logits,
                dim=-1
            )

        not_stressed = probabilities[0, 0].item()
        stressed = probabilities[0, 1].item()

        predicted_class = int(
            probabilities.argmax(dim=-1).item()
        )

        label = (
            "stressed" if predicted_class == 1
            else "not_stressed"
        )

        return {
            "prediction": label,
            "stress_probability": round(stressed * 100, 2),
            "not_stressed_probability": round(
                not_stressed * 100, 2
            ),
            "model": "StudentNet-Wav2Vec2",
            "device": str(self.device),
            "status": "success"
        }


_stress_predictor = None


def get_stress_predictor():
    """Return a lazily initialized predictor singleton.

    Loading the Hugging Face and Wav2Vec2 models can download sizeable assets, so
    it must not happen merely by importing this module.
    """
    global _stress_predictor

    if _stress_predictor is None:
        _stress_predictor = AstraStressPredictor()

    return _stress_predictor
