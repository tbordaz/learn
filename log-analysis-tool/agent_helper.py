from smolagents import CodeAgent
from smolagents import tool
import os
import pdb
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Define Ollama client class
class OllamaModel:
    def __init__(self, model_name=None, api_base=None):
        """
        Initialize the Ollama model client
        
        Args:
            model_name: Name of the Ollama model to use (defaults to env var or llama3.2)
            api_base: Base URL for Ollama API (defaults to env var or http://localhost:11434)
        """
        # Reload environment variables to ensure we have the latest
        load_dotenv(override=True)
        
        # Always prioritize explicitly passed values over environment variables
        if api_base is not None:
            self.api_base = api_base
        else:
            self.api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
            
        if model_name is not None:
            self.model_name = model_name
        else:
            self.model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        # Ensure API base is not empty
        if not self.api_base or self.api_base.strip() == "":
            self.api_base = "http://localhost:11434"
            
        print(f"OllamaModel initialized with API base: {self.api_base}")
        
    def __call__(self, prompt, **kwargs):
        """Make the class callable, required by smolagents"""
        # If prompt is not a string (e.g., a list or dict), convert it to a string
        if not isinstance(prompt, str):
            try:
                prompt = json.dumps(prompt)
            except:
                # If json conversion fails, try string conversion
                prompt = str(prompt)
        return self.generate(prompt, **kwargs)
        
    def generate(self, prompt, **kwargs):
        """Generate text using Ollama API"""
        url = f"{self.api_base}/api/generate"
        
        # Ensure prompt is a string
        if not isinstance(prompt, str):
            try:
                prompt = json.dumps(prompt)
            except:
                prompt = str(prompt)
        
        # Get timeout from environment variable or use default (300 seconds/5 minutes)
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "300"))
        
        # Default payload with optimized parameters for better performance
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            # Add performance optimization parameters
            "options": {
                "temperature": 0.3,       # Lower temperature for more focused responses
                "top_p": 0.9,             # Nucleus sampling for better quality
                "top_k": 40,              # Limit vocabulary for faster responses
                "num_predict": 2048,      # Maximum tokens to generate (adjust as needed)
                "num_ctx": 4096           # Context window size
            }
        }
        
        # Add any additional parameters or override defaults
        for key, value in kwargs.items():
            if key == "options" and isinstance(value, dict):
                # Merge options dictionaries
                for opt_key, opt_value in value.items():
                    payload["options"][opt_key] = opt_value
            elif key not in payload and value is not None:
                payload[key] = value
        
        try:
            # Log request parameters in debug mode
            if os.getenv("DEBUG") == "1":
                print(f"DEBUG: Sending request to Ollama with timeout={timeout}s and options={payload.get('options', {})}")
            
            # Use timeout from environment variable
            response = requests.post(url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama at {self.api_base}. Is Ollama running?")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to Ollama at {self.api_base} timed out after {timeout} seconds")
        except Exception as e:
            raise Exception(f"Error communicating with Ollama: {str(e)}")

def is_ollama_available(api_base=None):
    """
    Check if Ollama is available at the specified API base URL
    
    Args:
        api_base: Base URL for Ollama API (defaults to env var or http://localhost:11434)
        
    Returns:
        bool: True if Ollama is available, False otherwise
    """
    # Reload environment variables to ensure we have the latest
    load_dotenv(override=True)
    
    # Always prioritize explicitly passed values
    if api_base is None:
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    
    # Ensure API base is not empty
    if not api_base or api_base.strip() == "":
        api_base = "http://localhost:11434"
    
    print(f"Checking Ollama availability at: {api_base}")
    
    try:
        # Use a very short timeout to quickly detect if Ollama is available
        response = requests.get(f"{api_base}/api/version", timeout=0.5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking Ollama availability: {e}")
        return False

def is_ai_enhancement_enabled():
    """
    Check if AI enhancement is enabled based on:
    1. Environment variable DISABLE_AI_ENHANCEMENT not set to "true"
    2. Ollama API being available
    
    Returns:
        bool: True if AI enhancement is enabled, False otherwise
    """
    # Check if Ollama is disabled by environment variable
    not_disabled = os.getenv("DISABLE_AI_ENHANCEMENT") != "true"
    
    # Check if Ollama is running
    ollama_available = is_ollama_available()
    
    return ollama_available and not_disabled

def get_available_ollama_models(api_base=None):
    """
    Get list of available Ollama models
    
    Args:
        api_base: Base URL for Ollama API (defaults to env var or http://localhost:11434)
        
    Returns:
        list: List of available model names or default list if unavailable
    """
    # Reload environment variables to ensure we have the latest
    load_dotenv(override=True)
    
    # Always prioritize explicitly passed values
    if api_base is None:
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    
    # Ensure API base is not empty
    if not api_base or api_base.strip() == "":
        api_base = "http://localhost:11434"
    
    # Check if Ollama is available first before trying to get models
    if not is_ollama_available(api_base):
        return ["llama3.2", "llama3.1", "deepseek-r1"]
    
    try:
        response = requests.get(f"{api_base}/api/tags", timeout=1.0)
        
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            return models if models else ["llama3.2", "llama3.1", "deepseek-r1"]
        
        return ["llama3.2", "llama3.1", "deepseek-r1"]
    except Exception:
        # Default models if Ollama is not available
        return ["llama3.2", "llama3.1", "deepseek-r1"]

# Simple function version
def enhance_solution_direct(model, problem, solution, root_cause, further_investigations):
    """Direct implementation of solution enhancement without using the agent framework"""
    #log_examples_text = "\n".join(log_examples) if log_examples else "No log examples available"
    
    # Create a more concise prompt to reduce token usage
    prompt = f"""Enhance this log analysis solution:
Problem: {problem}
Basic solution: {solution}
Root cause: {root_cause}
Further investigations: {further_investigations}

Provide a detailed explanation of proposed solution and root caues. Also describe specific steps to resolve the issue for which you may inspirate yourself from the suggested investigations."""
#Provide a detailed explanation and specific steps to resolve the issue."""
    
    try:
        # Debug output to see the generated content
        if os.getenv("DEBUG") == "1":
            print(f"\nPrompt for {problem}:\n{prompt}\n")
        
        # Set options to optimize for this specific use case
        options = {
            "temperature": 0.5,      # Lower temperature for more deterministic output
            "top_p": 0.85,           # Slightly more focused token selection
            "num_predict": 2000      # Cap the output length to avoid timeouts
        }
        
        enhanced_solution = model(prompt, options=options)
        
        # Debug output to see the enhanced solution
        if os.getenv("DEBUG") == "1":
            print(f"\nEnhanced solution for {problem}:\n{enhanced_solution[:1000]}...\n")
            print(f"Enhanced solution length: {len(enhanced_solution)} characters")
            
        # Check if result is empty or very short
        if not enhanced_solution or len(enhanced_solution) < 20:
            print(f"⚠️ Warning: Enhanced solution for '{problem}' is too short or empty. Using original solution.")
            return solution
            
        #pdb.set_trace()
        return enhanced_solution
    except TimeoutError as e:
        print(f"⚠️ Timeout error enhancing solution for '{problem}': {e}")
        print(f"Using original solution due to timeout. Consider increasing the timeout value.")
        return solution
    except Exception as e:
        print(f"❌ Error generating enhancement for '{problem}': {e}")
        return solution  # Return original solution on error

# Keep the tool definition for compatibility with smolagents
@tool
def enhance_solution(problem_description: str, existing_solution: str, log_patterns: list) -> dict:
    """
    Generate an enhanced solution with better explanation for a log issue.
    
    Args:
        problem_description: Description of the identified problem
        existing_solution: Current solution suggestion
        log_patterns: Example log patterns related to the issue
    
    Returns:
        Enhanced solution with detailed explanation
    """
    # This is just a function signature - the LLM will implement the logic
    pass

def get_agent(model_name=None, api_base=None):
    """
    Initialize and return the solution enhancement agent
    
    Args:
        model_name: Name of the Ollama model to use (defaults to env var or llama3.2)
        api_base: Base URL for Ollama API (defaults to env var)
        
    Returns:
        tuple: (agent, model) - The CodeAgent instance and model instance
    """
    model = OllamaModel(model_name, api_base)
    
    # For compatibility - but we'll use the direct approach
    agent = CodeAgent(
        model=model,
        tools=[enhance_solution]
    )
    
    return agent, model

def enhance_solutions(analysis_results):
    """
    Enhance the solutions in the analysis results with better explanations.
    
    Args:
        analysis_results: The original analysis results with basic solutions
        
    Returns:
        Updated analysis results with enhanced solutions
    """
    # Check if AI enhancement is enabled
    if not is_ai_enhancement_enabled():
        print("🔴 AI Enhancement is DISABLED (Ollama not available or explicitly disabled)")
        analysis_results["ai_enhancement_used"] = False
        return analysis_results
    
    try:
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        print(f"🟢 AI Enhancement is ENABLED - Enhancing solutions with Ollama model {model_name}")
        
        agent, model = get_agent(model_name, api_base)
        original_solutions = analysis_results.get("solutions", [])
        enhanced_solutions = []
        
        if os.getenv("DEBUG") == "1":
            print(f"DEBUG: Original solutions count: {len(original_solutions)}")
            print(f"DEBUG: Original solutions: {original_solutions[:1]}")
        
        for solution in original_solutions:
            # Extract required information
            problem = solution.get("problem", "")
            basic_solution = solution.get("solution", "")
            
            # Find related log patterns
            patterns = []
            for pattern in analysis_results.get("analysis", {}).get("error_patterns", []):
                if any(keyword in pattern.get("pattern", "").lower() for keyword in problem.lower().split()):
                    patterns.append(pattern.get("pattern", ""))
            
            # Only use the first 3 patterns to keep prompt size reasonable
            root_cause = analysis_results.get("root cause", [])
            further_investigations = analysis_results.get("further investigations", [])
            
            print(f"⚙️ Enhancing solution for: {problem}")
            
            # First attempt with normal parameters
            enhanced_solution_text = enhance_solution_direct(model, problem, basic_solution, root_cause, further_investigations)
            
            # Check if the enhancement succeeded
            if enhanced_solution_text == basic_solution:
                if os.getenv("DEBUG") == "1":
                    print(f"DEBUG: Enhancement failed for {problem}, using original solution")
                
                # If enhancement failed, keep original solution but mark as not enhanced
                enhanced_solution = {
                    "problem": problem,
                    "solution": basic_solution,
                    "ai_enhanced": False
                }
            else:
                if os.getenv("DEBUG") == "1":
                    print(f"DEBUG: Enhancement successful for {problem}")
                
                # If enhancement succeeded, use the enhanced solution
                enhanced_solution = {
                    "problem": problem,
                    "solution": enhanced_solution_text,
                    "original_solution": basic_solution,
                    "ai_enhanced": True
                }
            
            enhanced_solutions.append(enhanced_solution)
        
        # Direct update of the solutions in the original results
        if os.getenv("DEBUG") == "1":
            print(f"DEBUG: Enhanced solutions before update: {len(enhanced_solutions)}")
            print(f"DEBUG: First enhanced solution: {enhanced_solutions[0].get('ai_enhanced', False)}")
        
        # Make a deep copy of the enhanced solutions
        analysis_results["solutions"] = enhanced_solutions.copy()
        analysis_results["ai_enhancement_used"] = True
        analysis_results["ollama_model_used"] = model_name
        
        # Debug output to verify update
        if os.getenv("DEBUG") == "1":
            print(f"DEBUG: Solutions in analysis_results after update: {len(analysis_results['solutions'])}")
            print(f"DEBUG: First solution has ai_enhanced={analysis_results['solutions'][0].get('ai_enhanced', False)}")
        
        print(f"✅ Solutions enhanced successfully with Ollama model: {model_name}")
        return analysis_results
    
    except ConnectionError as e:
        print(f"❌ Connection error with Ollama: {e}")
        analysis_results["ai_enhancement_used"] = False
        analysis_results["ai_error"] = str(e)
        return analysis_results  # Return original results on failure
    except Exception as e:
        print(f"❌ Error enhancing solutions with Ollama: {e}")
        analysis_results["ai_enhancement_used"] = False
        analysis_results["ai_error"] = str(e)
        return analysis_results  # Return original results on failure
