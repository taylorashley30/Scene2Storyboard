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
        self._load_model()
    
    def _load_model(self):
        """Load the BLIP model and processor"""
        try:
            print(f"Loading BLIP model: {self.model_name}")
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(self.model_name)
            
            # Set device (GPU if available, otherwise CPU)
            if torch.cuda.is_available():
                self.model.to('cuda')
                print("BLIP model loaded on GPU")
            else:
                print("BLIP model loaded on CPU")
                
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
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Load and preprocess the image
            raw_image = Image.open(image_path).convert('RGB')
            
            # Process the image
            inputs = self.processor(raw_image, return_tensors="pt")
            
            # Move inputs to the same device as the model
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            # Generate caption
            with torch.no_grad():
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