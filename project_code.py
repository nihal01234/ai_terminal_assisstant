import subprocess
import difflib
import ollama
import os
import re
import csv
import datetime
import platform
import psutil
import socket
import json
import requests
from typing import List, Dict, Optional, Tuple
import os, sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

class CommandHistory:
    def __init__(self, history_file="command_history.csv"):
        self.history_file = history_file
        self.ensure_history_file()
        try:
            
            self.gemini_api_key = "AIzaSyBAn17HEp1fQJT_7L0BxZw3TTOh99HHcsk"
            self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            
            
            if self.gemini_api_key == "AIzaSyBAn17HEp1fQJT_7L0BxZw3TTOh99HHcsk":
                self.gemini_available = True
                print("✅ Gemini API initialized successfully")
            else:
                print("⚠️ Gemini API key not provided. Falling back to Ollama for AI assistance.")
                self.gemini_available = False
        except Exception as e:
            print(f"⚠️ Failed to initialize Gemini API: {str(e)}. Falling back to Ollama.")
            self.gemini_available = False
    
    def ensure_history_file(self):
        """Create history file with headers if it doesn't exist"""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["timestamp", "command", "output", "success"])
                
    def add_entry(self, command: str, output: str, success: bool):
        """Add a new command entry to the history"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.history_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, command, output, success])
            
    def get_history(self) -> List[Dict]:
        """Get all history entries"""
        history = []
        with open(self.history_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                history.append(row)
        return history
    
    def display_history(self, limit: int = 20) -> List[Dict]:
        """Display recent command history with indices and return the history items"""
        history = self.get_history()
        recent_history = history[-limit:] if len(history) > limit else history
        
        print("\n📜 Command History:")
        print(f"{'#':<4} {'Timestamp':<20} {'Command':<40} {'Success':<10}")
        print("-" * 74)
        
        for i, entry in enumerate(recent_history, 1):
            success_marker = "✅" if entry["success"] == "True" else "❌"
            cmd_display = entry["command"][:37] + "..." if len(entry["command"]) > 40 else entry["command"]
            print(f"{i:<4} {entry['timestamp']:<20} {cmd_display:<40} {success_marker:<10}")
        
        return recent_history

class AITerminal:
    def __init__(self):
        self.commands = self.load_commands("commands.txt")
        self.history = CommandHistory()
        
        try:
            
            self.gemini_api_key = "AIzaSyBAn17HEp1fQJT_7L0BxZw3TTOh99HHcsk"
            self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            
            
            if self.gemini_api_key == "AIzaSyBAn17HEp1fQJT_7L0BxZw3TTOh99HHcsk":
                self.gemini_available = True
                print("✅ Gemini API initialized successfully")
            else:
                print("⚠️ Gemini API key not found. Falling back to Ollama for AI assistance.")
                self.gemini_available = False
        except Exception as e:
            print(f"⚠️ Failed to initialize Gemini API: {str(e)}. Falling back to Ollama.")
            self.gemini_available = False

    def load_commands(self, file_path: str) -> Dict[str, str]:
        """Load commands from configuration file"""
        commands = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if '|' in line:
                        parts = line.strip().split('|', 1)
                        if len(parts) == 2:
                            prompt, cmd = map(str.strip, parts)
                            commands[prompt.lower()] = cmd
        except FileNotFoundError:
            print(f"⚠️ Commands file '{file_path}' not found. Creating with default commands.")
            self.create_default_commands(file_path)
            commands = self.load_commands(file_path)
        return commands
    
    def create_default_commands(self, file_path: str):
        """Create a default commands file with basic commands"""
        default_commands = [
            "list files|dir",
            "show directory|cd",
            "process list|tasklist",
            "kill process by pid|taskkill /F /PID {pid}",
            "kill process by name|taskkill /F /IM {process_name}.exe",
            "ping website|ping {host}",
            "system info|systeminfo",
            "ip config|ipconfig /all",
            "check disk|chkdsk",
            "network stats|netstat -an",
            "echo text|echo {text}",
            "create directory|mkdir {dir_name}",
            "remove directory|rmdir {dir_name}",
            "copy file|copy {source} {destination}",
            "move file|move {source} {destination}",
            "delete file|del {file_name}",
            "show date|date /t",
            "show time|time /t",
            "clear screen|cls",
            "help|help {command}",
            "history|history"
        ]
        
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            for cmd in default_commands:
                file.write(f"{cmd}\n")
    
    def get_best_match(self, user_input: str, command_prompts: List[str]) -> Optional[str]:
        """Find the best matching command prompt using difflib"""
        matches = difflib.get_close_matches(user_input.lower(), command_prompts, n=1, cutoff=0.4)
        return matches[0] if matches else None
    
    def ask_ai(self, user_input: str, options: List[str]) -> str:
        """Query LLM to find most relevant command"""
        joined_prompts = '\n'.join(f"- {prompt}" for prompt in options)
        prompt = f"You are an AI terminal assistant. Given this user input: '{user_input}', choose the most relevant action from the list:\n{joined_prompts}\n\nRespond only with the exact matching action."
        
        try:
            response = ollama.chat(model="llama3.1", messages=[{"role": "user", "content": prompt}])
            return response['message']['content'].strip().lower()
        except Exception as e:
            print(f"⚠️ AI matching failed: {str(e)}")
            return ""
    
    def chat_with_gemini(self, message: str) -> str:
        """Use requests to interact with Gemini API"""
        url = f"{self.gemini_api_url}?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": message}]
            }]
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"⚠️ Unexpected Gemini response structure: {result}")
                return "Error: Unexpected API response structure"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def ai_helper(self, query: str) -> str:
        """Get general help from AI assistant for a natural language query"""
        if self.gemini_available:
            try:
                prompt = f"""
                You are an AI terminal assistant specialized in providing help for command line questions.
                
                Query: {query}
                
                Provide a clear, concise, and practical answer with examples where helpful.
                Focus on explaining how to solve the problem rather than theory.
                Include specific commands the user can try if appropriate.
                """
                
                return self.chat_with_gemini(prompt)
            except Exception as e:
                
                print(f"⚠️ Gemini API error: {str(e)}. Falling back to Ollama.")
                return self._ollama_helper(query)
        else:
            
            return self._ollama_helper(query)
            
    def _ollama_helper(self, query: str) -> str:
        """Fallback to use Ollama LLM"""
        try:
            prompt = f"I need help with this terminal/command prompt question: {query}\n\nProvide a clear, concise answer with examples if needed. Focus on being practical."
            response = ollama.chat(model="llama3.1", messages=[{"role": "user", "content": prompt}])
            return response['message']['content'].strip()
        except Exception as e:
            return f"⚠️ AI helper error: {str(e)}"
        
    def troubleshoot(self, problem: str) -> str:
        """Run troubleshooting for common terminal issues using Gemini API"""
        system_info = self.collect_system_info()
        
        if self.gemini_available:
            try:
                prompt = f"""
                You are an expert system troubleshooter specializing in terminal command issues.
                
                PROBLEM:
                "{problem}"
                
                SYSTEM INFORMATION:
                OS: {system_info['os']}
                Python: {system_info['python_version']}
                CPU Usage: {system_info['cpu_usage']}%
                Memory: {system_info['memory_used']}/{system_info['memory_total']} GB
                Disk Space: {system_info['disk_free']}/{system_info['disk_total']} GB
                Network: {system_info['network_status']}
                
                Please provide:
                1. Most likely root causes of the issue
                2. Step-by-step troubleshooting instructions
                3. Specific commands to run to fix the problem
                4. Preventive measures for the future
                
                Be concise, practical, and focus on actionable solutions.
                """
                
                return self.chat_with_gemini(prompt)
            except Exception as e:
                
                print(f"⚠️ Gemini API error: {str(e)}. Falling back to Ollama.")
                return self._ollama_troubleshoot(problem, system_info)
        else:
            
            return self._ollama_troubleshoot(problem, system_info)
    
    def _ollama_troubleshoot(self, problem: str, system_info: Dict) -> str:
        """Fallback troubleshooting using Ollama"""
        try:
            prompt = f"""
            I'm having this problem with my terminal: "{problem}"
            
            Here's my system information:
            OS: {system_info['os']}
            Python: {system_info['python_version']}
            CPU Usage: {system_info['cpu_usage']}%
            Memory: {system_info['memory_used']}/{system_info['memory_total']} GB
            Disk Space: {system_info['disk_free']}/{system_info['disk_total']} GB
            Network: {system_info['network_status']}
            
            Please diagnose the issue and suggest solutions. Be specific and provide commands I can try.
            """
            
            response = ollama.chat(model="llama3.1", messages=[{"role": "user", "content": prompt}])
            return response['message']['content'].strip()
        except Exception as e:
            return f"⚠️ Troubleshooting failed: {str(e)}\n\nBasic system info:\n{json.dumps(system_info, indent=2)}"
    
    def collect_system_info(self) -> Dict:
        """Gather basic system information for troubleshooting"""
        info = {}
        
    
        info['os'] = f"{platform.system()} {platform.release()} ({platform.version()})"
        info['python_version'] = platform.python_version()
        
        
        info['cpu_usage'] = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        info['memory_used'] = round(memory.used / (1024**3), 2)
        info['memory_total'] = round(memory.total / (1024**3), 2)
        
        
        disk = psutil.disk_usage('/')
        info['disk_free'] = round(disk.free / (1024**3), 2)
        info['disk_total'] = round(disk.total / (1024**3), 2)
        
        
        try:
            socket.create_connection(("www.google.com", 80))
            info['network_status'] = "Connected"
        except OSError:
            info['network_status'] = "Disconnected"
        
        return info
    
    def fill_placeholders(self, cmd_template: str) -> str:
        """Replace placeholders with user input"""
        matches = re.findall(r'{(.*?)}', cmd_template)
        for match in matches:
            match_lower = match.lower()
            if match_lower == 'pid':
                print("\n📋 Running processes:")
                subprocess.run("tasklist", shell=True)
                user_val = input("\n🔍 Enter the PID of the process to kill: ")
                cmd_template = cmd_template.replace("{pid}", user_val)
            elif match_lower == 'process_name':
                print("\n📋 Running processes:")
                subprocess.run("tasklist", shell=True)
                user_val = input("\n🔍 Enter the name of the process (without .exe): ")
                cmd_template = cmd_template.replace("{process_name}", user_val)
            elif match_lower == 'host':
                user_val = input("🌐 Enter website or IP to ping: ")
                cmd_template = cmd_template.replace("{host}", user_val)
            else:
                user_val = input(f"✏️ Enter value for '{match}': ")
                cmd_template = cmd_template.replace(f"{{{match}}}", user_val)
        return cmd_template
    
    def run_command(self, cmd: str) -> Tuple[str, bool]:
        """Execute command and return output and success status"""
        print(f"\n🛠️ Running: {cmd}\n")
        output = ""
        success = False
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            output = result.stdout + result.stderr
            print("📄 Output:\n" + output)
            success = True
        except subprocess.CalledProcessError as e:
            error_code = e.returncode
            error_output = e.stderr if e.stderr else e.stdout
            
            output = f"Command failed with exit code {error_code}:\n{error_output}"
            print(f"❌ {output}")
            
            
            suggestions = self.suggest_error_fix(cmd, error_code, error_output)
            if suggestions:
                print("\n🔍 Troubleshooting suggestions:")
                print(suggestions)
                output += f"\n\nTroubleshooting suggestions:\n{suggestions}"
                
            
            if input("\nWould you like me to run a detailed troubleshooting analysis? (y/n): ").lower() == 'y':
                troubleshooting = self.troubleshoot(f"Command '{cmd}' failed with: {error_output}")
                print(f"\n🔧 Detailed troubleshooting:\n{troubleshooting}")
                output += f"\n\nDetailed troubleshooting:\n{troubleshooting}"
        except Exception as e:
            output = f"Error: {str(e)}"
            print(f"❌ {output}")
            
            
            print("\n⚠️ Unexpected error occurred. This might be due to:")
            print("- Invalid command syntax")
            print("- Missing permissions")
            print("- System resource issues")
            
            if input("\nWould you like me to run troubleshooting? (y/n): ").lower() == 'y':
                troubleshooting = self.troubleshoot(f"Unexpected error with command '{cmd}': {str(e)}")
                print(f"\n🔧 Troubleshooting:\n{troubleshooting}")
                output += f"\n\nTroubleshooting:\n{troubleshooting}"
            
        return output, success

    def suggest_error_fix(self, cmd: str, error_code: int, error_output: str) -> str:
        """Provide quick suggestions for common command errors using Gemini"""
        if self.gemini_available:
            try:
                prompt = f"""
                You are an expert terminal troubleshooter. Help diagnose this command error:
                
                Command: {cmd}
                Error code: {error_code}
                Error output: {error_output}
                
                Provide 3-4 bullet points with:
                • Most likely causes
                • Specific solutions the user can try
                • Commands they can run to resolve the issue
                
                Be concise, practical, and straightforward. Format as bullet points.
                """
                
                return self.chat_with_gemini(prompt)
            except Exception as e:
                print(f"⚠️ Gemini API error: {str(e)}. Using rule-based suggestions.")
                return self._rule_based_suggestions(cmd, error_code, error_output)
        else:
            return self._rule_based_suggestions(cmd, error_code, error_output)
            
    def _rule_based_suggestions(self, cmd: str, error_code: int, error_output: str) -> str:
        """Rule-based error suggestions when AI is unavailable"""
        suggestions = []
        
        
        if "is not recognized as an internal or external command" in error_output:
            cmd_name = cmd.split()[0]
            suggestions.append(f"• Command '{cmd_name}' not found. Check if it's installed and in your PATH.")
            suggestions.append(f"• Try using the full path to the executable.")
        
        elif "Access is denied" in error_output:
            suggestions.append("• You may need administrator privileges. Try running the terminal as administrator.")
            suggestions.append("• Check if you have permission to access the specified files/directories.")
        
        elif "No such file or directory" in error_output or "The system cannot find the file specified" in error_output:
            suggestions.append("• The specified file or directory doesn't exist.")
            suggestions.append("• Check the path and try again, or use 'dir' to list available files.")
        
        elif "syntax error" in error_output.lower():
            suggestions.append("• There's a syntax error in your command.")
            suggestions.append("• Check for missing quotes, incorrect parameters, or typos.")
        
        
        if not suggestions:
            suggestions.append("• Double-check command syntax and parameters.")
            suggestions.append("• Verify required services or dependencies are running.")
            suggestions.append("• Check system resources (disk space, memory) with 'systeminfo'.")
        
        return "\n".join(suggestions)
    
    def handle_built_in_commands(self, user_input: str) -> bool:
        """Handle special built-in commands"""
        
        help_match = re.match(r'{help\s+(.*)}', user_input)
        if help_match:
            query = help_match.group(1)
            help_text = self.ai_helper(query)
            print(f"\n🤖 AI Helper:\n{help_text}")
            self.history.add_entry(f"{{help {query}}}", help_text, True)
            return True
            
        
        troubleshoot_match = re.match(r'{troubleshoot\s+(.*)}', user_input)
        if troubleshoot_match:
            problem = troubleshoot_match.group(1)
            solution = self.troubleshoot(problem)
            print(f"\n🔧 Troubleshooting:\n{solution}")
            self.history.add_entry(f"{{troubleshoot {problem}}}", solution, True)
            return True
            
        
        if user_input.lower() == "history":
            recent_history = self.history.display_history()
            if recent_history:
                try:
                    choice = input("\nEnter the number to view full output (or press Enter to continue): ")
                    if choice.isdigit() and 1 <= int(choice) <= len(recent_history):
                        entry = recent_history[int(choice) - 1]
                        print(f"\n📝 Command: {entry['command']}")
                        print(f"⏱️ Time: {entry['timestamp']}")
                        print(f"📄 Output:\n{entry['output']}")
                except ValueError:
                    pass
            self.history.add_entry("history", "Displayed command history", True)
            return True
            
        return False

    def run(self):
        """Main terminal loop"""
        print("🚀 Enhanced AI Terminal started. Type 'exit' to quit.")
        print("💡 Special commands: {help query}, {troubleshoot issue}, history")
        
        while True:
            user_input = input("\n🖥️ AI Terminal > ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Exiting AI Terminal.")
                break
                
            
            if self.handle_built_in_commands(user_input):
                continue
                
            
            best_prompt = self.get_best_match(user_input, list(self.commands.keys()))
            if not best_prompt:
                best_prompt = self.ask_ai(user_input, list(self.commands.keys()))
                
            if best_prompt in self.commands:
                cmd_template = self.commands[best_prompt]
                full_cmd = self.fill_placeholders(cmd_template)
                output, success = self.run_command(full_cmd)
                self.history.add_entry(full_cmd, output, success)
            else:
                print("⚠️ I didn't understand that command.")
                self.history.add_entry(user_input, "Command not recognized", False)

if __name__ == "__main__":
    try:
        terminal = AITerminal()
        terminal.run()
    except KeyboardInterrupt:
        print("\n\n👋 AI Terminal was interrupted. Exiting.")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        print("Please restart the terminal or run troubleshooting with: {troubleshoot terminal crash}")