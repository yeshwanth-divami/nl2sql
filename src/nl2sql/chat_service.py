import json
import os
from typing import Optional, Dict, Any
import httpx
from .config.endpoints import API_ENDPOINTS
from .config.constants import DEFAULT_ASSISTANT_ID


class ChatService:
    """Python implementation of the ChatService for handling chat sessions and messaging."""
    
    def __init__(self):
        self.auth_token = os.getenv('AUTH_TOKEN')
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.default_persona_id = DEFAULT_ASSISTANT_ID
        
    async def _fetch_with_auth(self, path: str, payload: Dict[str, Any]) -> httpx.Response:
        """Make an authenticated POST request to the API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{API_ENDPOINTS['BASE_URL']}{path}",
                    headers={
                        **self.headers,
                        'Authorization': f'Bearer {self.auth_token}',
                    },
                    json=payload,
                )
                return response
            except Exception as e:
                print(f"HTTP request failed: {e}")
                raise
    
    async def _create_chat_session_id(self, assistant_id: str) -> str:
        """Create a new chat session and return the session ID."""
        response = await self._fetch_with_auth(
            API_ENDPOINTS['CREATE_CHAT_SESSION'],
            {
                'persona_id': int(assistant_id),
                'description': None,
            }
        )
        
        if not response.is_success:
            error_text = response.text
            raise Exception(f"Failed to create chat session: {error_text}")
        
        data = response.json()
        if 'chat_session_id' not in data:
            raise Exception('Missing chat_session_id in response')
        
        return data['chat_session_id']
    
    async def _stream_response_text(self, response: httpx.Response) -> str:
        """Stream the response and extract answer pieces from JSON chunks."""
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        if not response.is_success:
            error_text = response.text
            print(f"API Error: {error_text}")
            raise Exception(f"API request failed with status {response.status_code}: {error_text}")
        
        full_text = ''
        chunk_count = 0
        
        try:
            async for chunk in response.aiter_bytes():
                chunk_count += 1
                chunk_text = chunk.decode('utf-8')
                print(f"Chunk {chunk_count}: {chunk_text[:200]}...")  # Show first 200 chars
                
                lines = chunk_text.split('\n')
                
                for line in lines:
                    if line.strip() and line.startswith('{'):
                        try:
                            json_data = json.loads(line)
                            print(f"Parsed JSON: {json_data}")
                            
                            # Check for errors first
                            if 'error' in json_data:
                                error_msg = json_data['error']
                                print(f"API Error in response: {error_msg}")
                                raise Exception(f"API Error: {error_msg}")
                            
                            # Look for message content in the obj.content field
                            if 'obj' in json_data and isinstance(json_data['obj'], dict):
                                obj = json_data['obj']
                                if obj.get('type') == 'message_delta' and 'content' in obj:
                                    content = obj['content']
                                    full_text += content
                                    print(f"Added message content: {content}")
                            
                            # Also check for answer_piece (in case API format varies)
                            if 'answer_piece' in json_data:
                                full_text += json_data['answer_piece']
                                print(f"Added answer_piece: {json_data['answer_piece']}")
                                
                        except json.JSONDecodeError as e:
                            print(f"JSON parse error for line: {line[:100]}... Error: {e}")
                            continue                # Break if we've been streaming for too long without getting data
                if chunk_count > 100 and not full_text:
                    print("Too many chunks without data, breaking...")
                    break
                    
        except Exception as e:
            print(f"Error during streaming: {e}")
            raise
        
        print(f"Final full_text before cleaning: '{full_text}'")
        print(f"Total chunks processed: {chunk_count}")
        
        # Remove <think> tags and return trimmed text
        import re
        cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', full_text).strip()
        print(f"Final cleaned text: '{cleaned_text}'")
        return cleaned_text
    
    async def create_chat_session(self, prompt: str, assistant_id: str) -> str:
        """Create a chat session and send a message, returning the response."""
        try:
            print(f"Creating chat session for prompt: '{prompt}' with assistant_id: '{assistant_id}'")
            
            chat_session_id = await self._create_chat_session_id(assistant_id)
            print(f"Created chat session ID: {chat_session_id}")
            
            payload = {
                'alternate_assistant_id': assistant_id,
                'chat_session_id': chat_session_id,
                'parent_message_id': None,
                'message': prompt,
                'prompt_id': None,
                'search_doc_ids': None,
                'file_descriptors': [],
                'user_file_ids': [],
                'user_folder_ids': [],
                'regenerate': False,
                'retrieval_options': {
                    'run_search': 'always',
                    'real_time': True,
                    'filters': {
                        'source_type': None,
                        'document_set': None,
                        'time_cutoff': None,
                        'tags': [],
                        'user_file_ids': None,
                    },
                },
                'use_agentic_search': False,
            }
            
            # Only add llm_override if we have valid values
            model_provider = os.getenv('LLM_MODEL_PROVIDER')
            model_version = os.getenv('LLM_MODEL_VERSION')
            
            # Try without LLM override first to see if API has defaults
            if False:  # Temporarily disabled
                payload['llm_override'] = {
                    'model_provider': model_provider,
                    'model_version': model_version,
                    'temperature': 0.5,
                }
            
            print(f"Sending payload to API: {json.dumps(payload, indent=2)}")
            
            response = await self._fetch_with_auth(
                API_ENDPOINTS['SEND_MESSAGE'],
                payload
            )
            print("Response from chat:", response)

            result = await self._stream_response_text(response)
            print(f"Final result: '{result}'")
            return result
            
        except Exception as e:
            print(f"Error in create_chat_session: {e}")
            raise Exception(f"Chat service error: {str(e)}")
