#!/usr/bin/env python3
"""
Simple log analysis script that uses GenAI to enhance the analysis.
This will search log files for specific terms and analyze the results.
"""

import os
import re
import sys
import argparse
import json
from datetime import datetime
from collections import Counter, defaultdict
from agent_helper import enhance_solutions, is_ai_enhancement_enabled
    
def find_log_files(directory, max_files=100):
    """Find all log files in a directory"""
    log_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.log'):
                log_files.append(os.path.join(root, file))
            if len(log_files) >= max_files:
                break
    return log_files

def search_files_for_term(files, search_term, max_matches=1000):
    """Search files for a specific term"""
    matches = []
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for i, line in enumerate(f):
                    if search_term.lower() in line.lower():
                        matches.append({
                            'file': file_path,
                            'line_number': i + 1,
                            'content': line.strip()
                        })
                        if len(matches) >= max_matches:
                            break
            if len(matches) >= max_matches:
                break
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
    return matches

def parse_log_entry(line):
    """Parse a log line into structured data"""
    log_entry = {'raw': line}
    
    # Extract timestamp
    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
    if timestamp_match:
        log_entry["timestamp"] = timestamp_match.group(1)
    
    # Extract severity
    severity_match = re.search(r'\b(ERROR|INFO|WARNING|DEBUG|CRITICAL|WARN|FATAL)\b', line, re.IGNORECASE)
    if severity_match:
        log_entry["severity"] = severity_match.group(1).upper()
    else:
        log_entry["severity"] = "UNKNOWN"
    
    # Extract component and message
    if timestamp_match:
        remainder = line[timestamp_match.end():].strip()
    else:
        remainder = line
        
    if severity_match:
        component_msg = remainder.replace(severity_match.group(0), "", 1).strip()
        
        # Extract component (in brackets or before colon)
        component_match = re.search(r'^\[([^\]]+)\]|^([^:]+):', component_msg)
        if component_match:
            component = component_match.group(1) or component_match.group(2)
            log_entry["component"] = component.strip()
            
            # Message is the rest
            if component_match.group(1):  # [component] format
                log_entry["message"] = component_msg[component_match.end():].strip()
            else:  # component: format
                log_entry["message"] = component_msg[component_match.end():].strip()
        else:
            log_entry["message"] = component_msg
    else:
        log_entry["message"] = remainder
    
    return log_entry

def analyze_log_entries(entries):
    """Analyze log entries to extract patterns and insights"""
    total_entries = len(entries)
    severities = Counter()
    components = Counter()
    errors_by_component = defaultdict(list)
    timestamps = []
    
    # Extract data
    for entry in entries:
        parsed = parse_log_entry(entry['content'])
        severities[parsed.get('severity', 'UNKNOWN')] += 1
        
        if 'component' in parsed:
            components[parsed['component']] += 1
            if parsed.get('severity') in ['ERROR', 'CRITICAL', 'FATAL']:
                errors_by_component[parsed['component']].append(parsed.get('message', ''))
        
        if 'timestamp' in parsed:
            timestamps.append(parsed['timestamp'])
    
    # Analyze time patterns
    time_pattern = None
    if timestamps:
        try:
            timestamps = sorted(timestamps)
            time_pattern = {
                'first_occurrence': timestamps[0],
                'last_occurrence': timestamps[-1],
                'total_occurrences': len(timestamps)
            }
        except Exception as e:
            print(f"Error analyzing timestamps: {e}")
    
    # Find most common error patterns
    error_patterns = []
    for component, errors in errors_by_component.items():
        for error in errors:
            # Look for common patterns in errors
            if error and len(error) > 10:  # Only consider substantial errors
                pattern = re.sub(r'\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b', '<ID>', error)  # Replace UUIDs
                pattern = re.sub(r'\d+', '<NUM>', pattern)  # Replace numbers
                error_patterns.append((component, pattern))
    
    common_patterns = Counter(error_patterns).most_common(10)
    
    return {
        'total_entries': total_entries,
        'severity_distribution': dict(severities),
        'components': dict(components),
        'time_pattern': time_pattern,
        'error_patterns': [{'component': comp, 'pattern': pat, 'count': count} 
                           for (comp, pat), count in common_patterns]
    }

def suggest_solutions(analysis):
    """Suggest solutions based on the analysis"""
    solutions = []
    
    # Check for connection issues
    connection_errors = any('connection' in pattern.lower() or 'timeout' in pattern.lower() or 'connect' in pattern.lower() 
                          for item in analysis.get('error_patterns', []) 
                          for pattern in [item['pattern'].lower()])
    
    if connection_errors:
        solutions.append({
            'problem': 'Connection issues',
            'solution': 'Check network connectivity between services and verify that all dependent services are running. Look for firewall or DNS issues.'
        })
    
    # Check for permission issues
    permission_errors = any('permission' in pattern.lower() or 'access' in pattern.lower() or 'denied' in pattern.lower() 
                          for item in analysis.get('error_patterns', []) 
                          for pattern in [item['pattern'].lower()])
    
    if permission_errors:
        solutions.append({
            'problem': 'Permission issues',
            'solution': 'Verify file and resource permissions. Check that service accounts have the necessary access rights.'
        })
    
    # Check for resource issues
    resource_errors = any('memory' in pattern.lower() or 'cpu' in pattern.lower() or 'capacity' in pattern.lower() or 'full' in pattern.lower()
                        for item in analysis.get('error_patterns', []) 
                        for pattern in [item['pattern'].lower()])
    
    if resource_errors:
        solutions.append({
            'problem': 'Resource constraints',
            'solution': 'Check system resources (memory, CPU, disk space). Consider scaling up infrastructure or optimizing resource usage.'
        })
    
    # Database issues
    db_errors = any('database' in pattern.lower() or 'db' in pattern.lower() or 'sql' in pattern.lower() or 'query' in pattern.lower()
                   for item in analysis.get('error_patterns', []) 
                   for pattern in [item['pattern'].lower()])
    
    if db_errors:
        solutions.append({
            'problem': 'Database issues',
            'solution': 'Check database connectivity, query performance, and database logs. Verify that database indices are properly set up.'
        })
    
    # General solution if nothing specific found
    if not solutions:
        if analysis.get('total_entries', 0) > 0:
            # Find component with the most errors
            severity_dist = analysis.get('severity_distribution', {})
            error_count = severity_dist.get('ERROR', 0) + severity_dist.get('CRITICAL', 0) + severity_dist.get('FATAL', 0)
            
            components = analysis.get('components', {})
            most_common_component = max(components.items(), key=lambda x: x[1])[0] if components else 'unknown'
            
            solutions.append({
                'problem': f'Multiple errors in {most_common_component} component',
                'solution': f'Review the {most_common_component} component logs in detail and check recent code changes or configuration updates to this component.'
            })
    
    return solutions

def main():
    parser = argparse.ArgumentParser(description="Log Analysis with AI assistance")
    parser.add_argument("--logs", type=str, default="./data/logs", help="Directory containing log files")
    parser.add_argument("--term", type=str, default="error", help="Search term for logs")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--disable-ai", action="store_true", help="Disable AI enhancement")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    # Set environment variable to control AI usage
    if args.disable_ai:
        os.environ["DISABLE_AI_ENHANCEMENT"] = "true"
        print("\n⚠️  AI Enhancement has been DISABLED via command-line flag\n")
    else:
        print("\n🔍 AI Enhancement status will be determined by API key availability\n")
    
    # Set debug mode
    if args.debug:
        os.environ["DEBUG"] = "1"
        print("\n🐞 Debug mode is ENABLED\n")
    
    # Verify log directory exists
    if not os.path.exists(args.logs):
        print(f"Error: Log directory '{args.logs}' does not exist")
        sys.exit(1)
    
    print(f"Searching in {args.logs} for term '{args.term}'...")
    
    # Find log files
    log_files = find_log_files(args.logs)
    print(f"Found {len(log_files)} log files")
    
    if args.verbose:
        print("Log files found:")
        for file in log_files[:10]:  # Show max 10 files
            print(f"  - {file}")
        if len(log_files) > 10:
            print(f"  ... and {len(log_files) - 10} more")
    
    # Search for term in files
    matches = search_files_for_term(log_files, args.term)
    print(f"Found {len(matches)} matches for term '{args.term}'")
    
    if args.verbose:
        print("Sample matches:")
        for match in matches[:5]:  # Show max 5 matches
            print(f"  - {match['file']}:{match['line_number']}: {match['content'][:100]}...")
    
    # Analyze log entries
    print("Analyzing log entries...")
    analysis = analyze_log_entries(matches)
    
    # Generate solution suggestions
    print("Generating solutions...")
    solutions = suggest_solutions(analysis)
    
    # Prepare the results
    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'search_term': args.term,
            'log_directory': args.logs,
            'total_files_searched': len(log_files),
            'total_matches': len(matches)
        },
        'matches': matches,
        'analysis': analysis,
        'solutions': solutions
    }
    
    # Use AI to enhance the solutions if possible
    ai_status = is_ai_enhancement_enabled()
    if ai_status:
        try:
            print("Enhancing solutions with AI...")
            results = enhance_solutions(results)
        except Exception as e:
            print(f"Error enhancing solutions: {e}")
            results["ai_enhancement_used"] = False
            results["ai_error"] = str(e)
    else:
        results["ai_enhancement_used"] = False
    
    # Output the results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {args.output}")
    else:
        # Print summary to console
        print("\n--- Analysis Summary ---")
        print(f"Total entries: {analysis['total_entries']}")
        
        if 'severity_distribution' in analysis:
            print("\nSeverity distribution:")
            for severity, count in analysis['severity_distribution'].items():
                print(f"  - {severity}: {count}")
        
        # Get the solutions from the results dictionary AFTER AI enhancement
        ai_enhanced_solutions = results.get('solutions', [])
        
        if ai_enhanced_solutions:
            print("\nSuggested solutions:")
            
            # Debug output for solutions
            if os.getenv("DEBUG") == "1":
                print(f"\nDEBUG: Total solutions: {len(ai_enhanced_solutions)}")
                for i, solution in enumerate(ai_enhanced_solutions):
                    print(f"DEBUG: Solution {i+1} keys: {list(solution.keys())}")
                    print(f"DEBUG: Is AI enhanced? {solution.get('ai_enhanced', False)}")
            
            for i, solution in enumerate(ai_enhanced_solutions, 1):
                problem = solution.get('problem', 'Unknown issue')
                
                # Determine which solution text to display - prefer AI enhanced if available
                if solution.get('ai_enhanced', False):
                    solution_text = solution.get('solution', '')
                else:
                    solution_text = solution.get('solution', '')
                    if os.getenv("DEBUG") == "1":
                        print(f"DEBUG: Using original solution for {problem} - AI enhancement not available")
                
                print(f"  {i}. {problem}")
                
                # Debug the content of the solution
                if os.getenv("DEBUG") == "1":
                    print(f"DEBUG: Solution {i} content length: {len(solution_text)}")
                    print(f"DEBUG: Solution {i} first 50 chars: {solution_text[:50]}...")
                
                # Only display the first 3-4 lines of the enhanced solution to keep it concise
                # Split by newlines and filter out empty lines
                solution_lines = [line for line in solution_text.split('\n') if line.strip()]
                if len(solution_lines) > 4:
                    # Display first 3 lines if the solution is very long
                    display_solution = '\n     '.join(solution_lines[:3]) + '\n     ...'
                else:
                    display_solution = '\n     '.join(solution_lines)
                
                print(f"     {display_solution}")
                
                # Add a line break for readability
                if i < len(ai_enhanced_solutions):
                    print("")
        
        if results.get("ai_enhancement_used", False):
            model_name = results.get("ollama_model_used", os.getenv("OLLAMA_MODEL", "default"))
            print(f"\n✨ Solutions were enhanced using Ollama model: {model_name}")
        elif results.get("ai_error"):
            print(f"\n⚠️ AI enhancement failed: {results.get('ai_error')}")
            if os.getenv("DEBUG") == "1":
                print(f"Detailed error: {results.get('ai_error')}")
        else:
            print("\n⚠️ AI enhancement was not used")

if __name__ == "__main__":
    main() 