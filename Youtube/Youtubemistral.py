import subprocess
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import os

@dataclass
class VideoInfo:
    video_id: str
    title: str
    description: str
    transcript: str
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None

class YouTubeSummarizer:
    MODELS = {
        "llama3": "llama3.3:latest",
        "mistral": "mistral",
        "llama2": "llama2",
        "mixtral": "mixtral-8x7b",
        "phi": "phi-2"
    }

    def __init__(self, model_type: str = "mistral", cache_dir: Path = Path("cache")):
        if model_type not in self.MODELS:
            raise ValueError(f"Invalid model type. Choose from: {list(self.MODELS.keys())}")
            
        self.model = self.MODELS[model_type]
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    async def get_transcript(self, video_id: str) -> str:
        try:
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--skip-download",
                "--sub-lang", "en",
                f"https://youtube.com/watch?v={video_id}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to download transcript: {result.stderr}")
                
            vtt_file = next(Path().glob(f"*{video_id}*.vtt"))
            transcript = self._parse_vtt(vtt_file)
            vtt_file.unlink()
            return transcript
            
        except Exception as e:
            self.logger.error(f"Error getting transcript: {str(e)}")
            return ""

    def _parse_vtt(self, vtt_file: Path) -> str:
        text_lines = []
        with open(vtt_file) as f:
            lines = f.readlines()[4:]
            
        for line in lines:
            line = line.strip()
            if line and not line[0].isdigit() and '-->' not in line:
                text_lines.append(line)
                
        return ' '.join(text_lines)

    def _get_cached_result(self, video_id: str) -> Optional[Tuple[str, List[str]]]:
        cache_file = self.cache_dir / f"{video_id}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return data["summary"], data["key_points"]
        return None

    def _cache_result(self, video_id: str, summary: str, key_points: List[str]):
        cache_file = self.cache_dir / f"{video_id}.json"
        cache_file.write_text(json.dumps({
            "summary": summary,
            "key_points": key_points,
            "model": self.model,
            "timestamp": datetime.now().isoformat()
        }))

    def _generate_with_ollama(self, prompt: str) -> str:
        try:
            import requests
            response = requests.post(
                "http://209.137.198.205:11434/api/generate",
                json={"model": self.model, "prompt": prompt}
            )
            if response.status_code == 200:
                # Stream the response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line)
                            if "response" in json_response:
                                full_response += json_response["response"]
                        except json.JSONDecodeError:
                            continue
                return full_response
            else:
                raise Exception(f"API error: {response.text}")
        except Exception as e:
            self.logger.error(f"Error generating with Ollama: {str(e)}")
            return ""

    def _chunk_text(self, text: str, max_length: int = 1500) -> List[str]:
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    async def generate_summary(self, video_info: VideoInfo) -> Tuple[str, List[str]]:
        cached = self._get_cached_result(video_info.video_id)
        if cached:
            return cached

        chunks = self._chunk_text(video_info.transcript, max_length=4000)
        summaries = []

        for chunk in chunks:
            prompt = f"""
            You are an expert technical analyst. Analyze this video transcript segment in detail:
            
            Context:
            Title: {video_info.title}
            Description: {video_info.description[:500]}
            
            Transcript segment:
            {chunk}
            
            Required analysis points:
            1. Detailed technical concepts and terminology explained
            2. Step-by-step implementation details
            3. System architecture and components
            4. Configuration parameters and settings
            5. Performance considerations
            6. Security implications
            7. Cost considerations
            8. Integration points
            9. Best practices with specific examples
            10. Common pitfalls and solutions

            Format:
            - Each topic should have 2-3 detailed paragraphs
            - Include specific commands, configurations, and parameters
            - Explain the reasoning behind technical decisions
            - Include real-world implications and use cases
            """
            summary = self._generate_with_ollama(prompt)
            if summary:
                summaries.append(summary)

        if not summaries:
            return "Failed to generate summary", []

        final_prompt = f"""
        You are creating a comprehensive technical documentation from these video summaries:

        {' '.join(summaries)}

        Generate a detailed technical analysis with the following structure:

        1. Executive Summary
        - High-level overview of the technology/service
        - Key benefits and use cases
        - Target audience and prerequisites

        2. Technical Architecture
        - Detailed component breakdown
        - System interactions and data flow
        - Scalability considerations
        - Security model and compliance

        3. Implementation Guide
        - Step-by-step setup instructions
        - Configuration parameters
        - Code examples where applicable
        - Integration points

        4. Operational Best Practices
        - Performance optimization
        - Monitoring and logging
        - Backup and disaster recovery
        - Cost optimization strategies

        5. Common Challenges and Solutions
        - Known limitations
        - Troubleshooting guides
        - Alternative approaches
        - Migration considerations

        6. Key Technical Points (separated by |)
        - List at least 10 specific technical points
        - Include version numbers, limits, and specific parameters
        - Highlight critical configuration options
        - Note important command-line options

        Format:
        - Use technical terms precisely
        - Include actual commands and configurations
        - Provide specific examples
        - Reference AWS service limits and quotas
        - Explain dependencies and prerequisites
        """

        result = self._generate_with_ollama(final_prompt)
        if not result:
            return "Failed to generate final summary", []

        parts = result.split('\n\n')
        summary = parts[0].strip()
        key_points = [p.strip() for p in parts[-1].split('|') if p.strip()]
        
        self._cache_result(video_info.video_id, summary, key_points)
        return summary, key_points

    async def process_video(self, video_id: str) -> VideoInfo:
        self.logger.info(f"Processing video: {video_id}")
        
        cmd = ["yt-dlp", "-J", f"https://youtube.com/watch?v={video_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        metadata = json.loads(result.stdout)

        video_info = VideoInfo(
            video_id=video_id,
            title=metadata["title"],
            description=metadata["description"],
            transcript="",
            key_points=[]
        )

        video_info.transcript = await self.get_transcript(video_id)
        video_info.summary, video_info.key_points = await self.generate_summary(video_info)
        
        return video_info

    async def process_videos(self, video_ids: List[str]) -> List[VideoInfo]:
        tasks = [self.process_video(video_id) for video_id in video_ids]
        return await asyncio.gather(*tasks)

async def main():
    # Example usage
    video_id = "nloLBcYnUfo"  # Replace with your video ID
    summarizer = YouTubeSummarizer(model_type="mistral")
    results = await summarizer.process_videos([video_id])
    
    for video in results:
        print(f"\nTitle: {video.title}")
        print(f"Summary: {video.summary}")
        print("\nKey Points:")
        for point in video.key_points:
            print(f"- {point}")

if __name__ == "__main__":
    asyncio.run(main())