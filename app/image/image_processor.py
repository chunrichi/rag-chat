import os
import cv2
import numpy as np
from PIL import Image, ImageOps
import logging
from datetime import datetime
from transformers import CLIPProcessor, CLIPModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.clip_model = None
        self.clip_processor = None
        
    def load_clip_model(self):
        """加载CLIP模型用于图片特征提取"""
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            logger.info("成功加载CLIP模型")
            return True
        except Exception as e:
            logger.error(f"加载CLIP模型失败: {str(e)}")
            return False
    
    def compress_image(self, input_path, output_path=None, quality=85, max_size=(1920, 1080)):
        """压缩图片"""
        if not output_path:
            # 生成默认输出路径
            base_name, ext = os.path.splitext(input_path)
            output_path = f"{base_name}_compressed{ext}"
        
        try:
            with Image.open(input_path) as img:
                # 转换为RGB模式（如果是RGBA）
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # 调整大小
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存图片
                img.save(output_path, optimize=True, quality=quality)
                
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                logger.info(f"图片压缩完成: {input_path} → {output_path}")
                logger.info(f"压缩率: {compression_ratio:.2f}% (原始: {original_size/1024:.2f}KB → 压缩后: {compressed_size/1024:.2f}KB)")
                
                return output_path
        except Exception as e:
            logger.error(f"压缩图片失败 {input_path}: {str(e)}")
            return None
    
    def convert_image_format(self, input_path, output_format='jpg'):
        """转换图片格式"""
        try:
            with Image.open(input_path) as img:
                base_name, _ = os.path.splitext(input_path)
                output_path = f"{base_name}.{output_format.lower()}"
                
                # 如果是PNG转JPG，需要处理透明背景
                if output_format.lower() == 'jpg' and img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # 使用alpha通道作为蒙版
                    background.save(output_path, quality=95)
                else:
                    img.save(output_path, quality=95)
                
                logger.info(f"图片格式转换完成: {input_path} → {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"转换图片格式失败 {input_path}: {str(e)}")
            return None
    
    def extract_image_features(self, image_path):
        """使用CLIP模型提取图片特征"""
        if not self.clip_model or not self.clip_processor:
            if not self.load_clip_model():
                return None
        
        try:
            image = Image.open(image_path)
            inputs = self.clip_processor(images=image, return_tensors="pt", padding=True)
            outputs = self.clip_model.get_image_features(**inputs)
            
            # 将特征转换为numpy数组
            features = outputs.detach().numpy()[0]
            
            logger.info(f"成功提取图片特征: {image_path}")
            return features
        except Exception as e:
            logger.error(f"提取图片特征失败 {image_path}: {str(e)}")
            return None
    
    def preprocess_image_for_vector_db(self, image_path, output_dir=None):
        """预处理图片用于向量数据库"""
        if not output_dir:
            output_dir = os.path.dirname(image_path)
        
        # 1. 压缩图片
        compressed_path = self.compress_image(image_path, max_size=(1024, 1024))
        if not compressed_path:
            return None
        
        # 2. 转换为统一格式（JPG）
        converted_path = self.convert_image_format(compressed_path, output_format='jpg')
        if not converted_path:
            converted_path = compressed_path  # 如果转换失败，使用压缩后的图片
        
        # 3. 提取特征
        features = self.extract_image_features(converted_path)
        
        # 4. 保存特征为npy文件
        base_name, _ = os.path.splitext(converted_path)
        features_path = f"{base_name}_features.npy"
        if features is not None:
            np.save(features_path, features)
            logger.info(f"图片特征已保存: {features_path}")
        
        # 5. 清理临时文件
        if compressed_path != converted_path and os.path.exists(compressed_path):
            os.remove(compressed_path)
        
        result = {
            "original_path": image_path,
            "processed_path": converted_path,
            "features_path": features_path if features is not None else None,
            "features": features.tolist() if features is not None else None
        }
        
        return result
    
    def process_images_in_directory(self, input_dir, output_dir=None):
        """处理目录中的所有图片"""
        if not output_dir:
            output_dir = os.path.join(input_dir, "processed")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 支持的图片格式
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]
        
        processed_results = []
        
        for filename in os.listdir(input_dir):
            file_path = os.path.join(input_dir, filename)
            if os.path.isfile(file_path) and os.path.splitext(filename)[1].lower() in image_extensions:
                # 复制文件到输出目录
                output_path = os.path.join(output_dir, filename)
                
                # 预处理图片
                result = self.preprocess_image_for_vector_db(file_path, output_dir)
                if result:
                    processed_results.append(result)
        
        return processed_results
    
    def get_image_metadata(self, image_path):
        """获取图片元数据"""
        try:
            with Image.open(image_path) as img:
                metadata = {
                    "filename": os.path.basename(image_path),
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "file_size": os.path.getsize(image_path),
                    "created_time": datetime.fromtimestamp(os.path.getctime(image_path)).strftime("%Y-%m-%d %H:%M:%S"),
                    "modified_time": datetime.fromtimestamp(os.path.getmtime(image_path)).strftime("%Y-%m-%d %H:%M:%S")
                }
                return metadata
        except Exception as e:
            logger.error(f"获取图片元数据失败 {image_path}: {str(e)}")
            return None
    
    def batch_process_images(self, image_paths, output_dir):
        """批量处理图片"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        results = []
        for image_path in image_paths:
            if os.path.exists(image_path):
                result = self.preprocess_image_for_vector_db(image_path, output_dir)
                if result:
                    results.append(result)
        
        return results

if __name__ == "__main__":
    # 测试代码
    processor = ImageProcessor()
    
    # 测试压缩图片
    # processor.compress_image("test.jpg", quality=80)
    
    # 测试格式转换
    # processor.convert_image_format("test.png", output_format="jpg")
    
    # 测试特征提取
    # processor.load_clip_model()
    # features = processor.extract_image_features("test.jpg")
    # if features is not None:
    #     print(f"特征向量维度: {len(features)}")
    #     print(f"特征向量前10个值: {features[:10]}")
    
    # 测试预处理
    # result = processor.preprocess_image_for_vector_db("test.png")
    # print(result)