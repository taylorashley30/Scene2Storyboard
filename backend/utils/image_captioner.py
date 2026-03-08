#!/usr/bin/env python3
"""
Image captioning utility using BLIP model
"""

import os
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

class ImageCaptioner:
    """Class for generating captions for images using BLIP model"""
    
    def __init__(self, model_name="Salesforce/blip-image-captioning-base"):
        """
        Initialize the BLIP model for image captioning
        
        Args:
            model_name (str): Hugging Face model name for BLIP
        """
        self.model_name = model_name
        self.processor = None
        self.model = None
        self.device = None

    def _select_device(self) -> str:
        """
        Pick best available device for inference.
        Priority: CUDA > MPS (Apple Silicon) > CPU
        """
        if torch.cuda.is_available():
            return "cuda"
        # MPS is available on Apple Silicon when using an MPS-enabled PyTorch build.
        if getattr(torch.backends, "mps", None) is not None:
            if torch.backends.mps.is_available() and torch.backends.mps.is_built():
                return "mps"
        return "cpu"
    
    def _load_model(self):
        """Load the BLIP model and processor"""
        try:
            print(f"Loading BLIP model: {self.model_name}")
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(self.model_name)

            self.device = self._select_device()
            self.model.to(self.device)
            self.model.eval()
            print(f"BLIP model loaded on {self.device.upper()}")
                
        except Exception as e:
            print(f"Error loading BLIP model: {e}")
            raise
    
    def caption_image(self, image_path):
        """
        Generate a caption for an image
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Generated caption for the image
        """
        try:
            # Lazily load BLIP so the API server can start instantly.
            if self.processor is None or self.model is None:
                self._load_model()

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Load and preprocess the image
            raw_image = Image.open(image_path).convert('RGB')
            
            # Process the image
            inputs = self.processor(raw_image, return_tensors="pt")
            
            # Move inputs to the same device as the model
            if self.device is not None and self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate caption
            with torch.inference_mode():
                out = self.model.generate(**inputs, max_length=50, num_beams=5)
            
            # Decode the generated caption
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            
            return caption.strip()
            
        except Exception as e:
            print(f"Error generating caption for {image_path}: {e}")
            return f"[Captioning error: {str(e)}]"
    
    def caption_images_batch(self, image_paths):
        """
        Generate captions for multiple images in batch
        
        Args:
            image_paths (list): List of image file paths
            
        Returns:
            list: List of generated captions
        """
        captions = []
        for image_path in image_paths:
            caption = self.caption_image(image_path)
            captions.append(caption)
        return captions 