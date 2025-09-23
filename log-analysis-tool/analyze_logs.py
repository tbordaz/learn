#!/usr/bin/env python3
"""
Simple log analysis script that uses GenAI to enhance the analysis.
This will search log files for specific terms and analyze the results.
"""

import os
import pdb
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

def check_abandon_high_etime(line, diag, results):
    """
    Check the ABANDON with targetop=xx and 'etime' that occured in
    the same second.
    """
    try:
        results_abandon_high_etime = results["abandon_high_etime"]
    except KeyError:
        results_abandon_high_etime = {
                'event_abandon_high_etime': []}
        results["abandon_high_etime"] = results_abandon_high_etime

    try:
        abandon_high_etime = diag["abandon_high_etime"]
    except KeyError:
        abandon_high_etime = {
                'severity': 'normal',
                'count': 0,
                'timematch': ""}
        diag["abandon_high_etime"] = abandon_high_etime

    nb_abandon_high_etime_threshold = 5
    high_etime_threshold = 20
    severity_threshold = {
            'fatal': 50,
            'critical': 30,
            'warning': 15}
    abandon_match = re.search(r'ABANDON targetop=[0-9]+ .*etime=(\d+).', line)
    if abandon_match:
        etime = int(abandon_match.group(1))
    else:
        etime = 0
    timestamp_match = re.search(r'^\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', line)

    if abandon_high_etime['timematch'] == "":
        abandon_high_etime['timematch'] = timestamp_match.group(1)

    if abandon_match:
        # This is an abandon
        if (timestamp_match.group(1) == abandon_high_etime['timematch']):
            # this record is in the same second than the previous one
            # If it is a long operation Just increase the number of time we detected it
            if (etime >= high_etime_threshold):
                abandon_high_etime['count'] = abandon_high_etime['count'] + 1
        else:
            # This record occurred in a next second, register the current one
            # at the condition it overpass the threshold
            if (abandon_high_etime['count'] >= nb_abandon_high_etime_threshold):
                #pdb.set_trace()
                # in case the number of abandon
                # exceeded the threshold, register it into the results
                for threshold in ['fatal', 'critical', 'warning']:
                    if severity_threshold[threshold] and abandon_high_etime["count"] >= severity_threshold[threshold]:
                        abandon_high_etime["severity"] = threshold
                        break
                new_event = {"count": abandon_high_etime["count"],
                             "timematch": abandon_high_etime["timematch"],
                             "severity": abandon_high_etime["severity"]}
                results_abandon_high_etime["event_abandon_high_etime"].append(new_event)

            abandon_high_etime['count'] = 1
            abandon_high_etime['timematch'] = timestamp_match.group(1)
    else:
        if (timestamp_match.group(1) == abandon_high_etime['timematch']):
            # different operation in the same second are ignored
            return

        # This is another operation, just check if timestamp change
        # and if it is so record the previous event
        if (abandon_high_etime['count'] >= nb_abandon_high_etime_threshold):
            #pdb.set_trace()
            # in case the number of abandon
            # exceeded the threshold, register it into the results
            for threshold in ['fatal', 'critical', 'warning']:
                if severity_threshold[threshold] and abandon_high_etime["count"] >= severity_threshold[threshold]:
                    abandon_high_etime["severity"] = threshold
                    break
            new_event = {"count": abandon_high_etime["count"],
                         "timematch": abandon_high_etime["timematch"],
                         "severity": abandon_high_etime["severity"]}
            results_abandon_high_etime["event_abandon_high_etime"].append(new_event)

        abandon_high_etime['count'] = 0
        abandon_high_etime['timematch'] = timestamp_match.group(1)

def check_abandon_too_late(line, diag, results):
    """
    Check the ABANDON with targetop=NOTFOUND that occured in
    the same second.
    """
    try:
        results_abandon_too_late = results["abandon_too_late"]
    except KeyError:
        results_abandon_too_late = {
                'event_abandon_too_late': []}
        results["abandon_too_late"] = results_abandon_too_late

    try:
        abandon_too_late = diag["abandon_too_late"]
    except KeyError:
        abandon_too_late = {
                'severity': 'normal',
                'count': 0,
                'timematch': ""}
        diag["abandon_too_late"] = abandon_too_late

    abandon_too_late_threshold = 10
    severity_threshold = {
            'fatal': 100,
            'critical': 50,
            'warning': 20}
    abandon_match = re.search(r'ABANDON targetop=NOTFOUND', line)
    timestamp_match = re.search(r'^\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', line)
    if abandon_match:
        #pdb.set_trace()
        if abandon_too_late['timematch'] == "":
            abandon_too_late['timematch'] = timestamp_match.group(1)

        if timestamp_match.group(1) == abandon_too_late['timematch']:
            # this record is in the same second than the previous one
            abandon_too_late['count'] = abandon_too_late['count'] + 1

        else:
            # This record occurred in a next second, reset the count
            if abandon_too_late['count'] >= abandon_too_late_threshold:
                #pdb.set_trace()
                # in case the number of abandon
                # exceeded the threshold, register it into the results
                for threshold in ['fatal', 'critical', 'warning']:
                    if severity_threshold[threshold] and abandon_too_late["count"] >= severity_threshold[threshold]:
                        abandon_too_late["severity"] = threshold
                        break
                new_event = {"count": abandon_too_late["count"],
                             "timematch": abandon_too_late["timematch"],
                             "severity": abandon_too_late["severity"]}
                results_abandon_too_late["event_abandon_too_late"].append(new_event)

            # This record is in a next second, reset the count
            # and the timematch
            abandon_too_late['count'] = 1
            abandon_too_late['timematch'] = timestamp_match.group(1)
    else:
        if abandon_too_late['timematch'] == timestamp_match.group(1):
            # ignore others events in the same second
            return
        else:
            # This record occurred in a next second, reset the count
            if abandon_too_late['count'] >= abandon_too_late_threshold:
                # in case the number of abandon
                # exceeded the threshold, register it into the results
                for threshold in ['fatal', 'critical', 'warning']:
                    if severity_threshold[threshold] and abandon_too_late["count"] >= severity_threshold[threshold]:
                        abandon_too_late["severity"] = threshold
                        break
                new_event = {"count": abandon_too_late["count"],
                             "timematch": abandon_too_late["timematch"],
                             "severity": abandon_too_late["severity"]}
                results_abandon_too_late["event_abandon_too_late"].append(new_event)

            # This record is in a next second, reset the count
            # and the timematch
            abandon_too_late['count'] = 0
            abandon_too_late['timematch'] = ""

def check_server_unresponsive(line, diag, results):
    """ The goal of this check is to detect that the server
    is no longer processing new operations. Only new incoming
    connections are logged by the accept thread.
    That means all workers were busy, unable to read operations
    and send results.
    diag will increased with 'server_unresponsive' record
    {'server_unresponsive': 
        {'severity': 'fatal', 
         'count': 0,
         'maxcount': 361,
         'occurence': 2,
         'occurence_time': ['03/Oct/2023:00:43:21', '03/Oct/2023:00:43:44']
         }
     }
    """
    unresponsive_threshold = 10
    severity_threshold = {
            'fatal': 150,
            'critical': 75,
            'warning': 10}
    try:
        results_unresponsive = results["server_unresponsive"]
    except KeyError:
        results_unresponsive = {
                'event_unresponsive': []}
        results["server_unresponsive"] = results_unresponsive

    try:
        server_unresponsive = diag["server_unresponsive"]
    except KeyError:
        server_unresponsive = {
                'severity': 'normal',
                'count': 0,
                'timematch': ""}
        diag["server_unresponsive"] = server_unresponsive

    incoming_conn_match = re.search(r'connection from', line, re.IGNORECASE)
    if incoming_conn_match:
        # This is a new incoming connection
        server_unresponsive["count"] = server_unresponsive["count"] + 1

        # if we overpass the threshold, count one more occurence
        if server_unresponsive["count"] == unresponsive_threshold:
            timestamp_match = re.search(r'^\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                server_unresponsive["timematch"] = timestamp_match.group(1)
    else:
        # This is the end of consecutive opened connections
        # in case the number of consecutive opened connections
        # exceeded the threshold, register it into the results
        if server_unresponsive["count"] >= unresponsive_threshold:
            #pdb.set_trace()
            # set the severity according to the size of consecutive new incoming connections
            for threshold in ['fatal', 'critical', 'warning']:
                if severity_threshold[threshold] and server_unresponsive["count"] >= severity_threshold[threshold]:
                    server_unresponsive["severity"] = threshold
                    break
            new_event = {"count": server_unresponsive["count"],
                         "timematch": server_unresponsive["timematch"],
                         "severity": server_unresponsive["severity"]}
            results_unresponsive["event_unresponsive"].append(new_event)

        # only reset the count
        server_unresponsive["severity"] = "normal"
        server_unresponsive["count"] = 0
        server_unresponsive["timematch"] = ""
        diag["server_unresponsive"] = server_unresponsive


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


def parse_log_entry(line, diag, results):
    """Parse a log line into structured data"""
    check_server_unresponsive(line, diag, results)
    check_abandon_too_late(line, diag, results)
    check_abandon_high_etime(line, diag, results)
    if re.search(r'conn=488 op=3 BIND', line, re.IGNORECASE):
        #pdb.set_trace()
        pass
    return
    log_entry = {'raw': line}
    
    #pdb.set_trace()
    # Extract timestamp
    timestamp_match = re.search(r'^\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', line)
    if timestamp_match:
        log_entry["timestamp"] = timestamp_match.group(1)
    
    # Extract SRCH etime
    etime_match = re.search(r'RESULT.*tag=101.*etime=(\d).(\d) ', line, re.IGNORECASE)
    if log_entry:
        log_entry["etime second"] = etime_match.group(1)
        log_entry["etime nsec"] = etime_match.group(2)
    else:
        log_entry["etime second"] = 0
        log_entry["etime nsec"] = 0

    if log_entry["etime second"] > 10:
        log_entry["severity"] = "WARNING"

    # Extract SRCH wtime
    wtime_match = re.search(r'RESULT.*tag=101.*wtime=(\d).(\d) ', line, re.IGNORECASE)
    if log_entry:
        log_entry["wtime second"] = etime_match.group(1)
        log_entry["wtime nsec"] = etime_match.group(2)
    else:
        log_entry["wtime second"] = 0
        log_entry["wtime nsec"] = 0

    if log_entry["wtime second"] > 0:
        log_entry["severity"] = "CRITICAL"

    # Extract consecutive incoming connections
    incoming_conn_match = re.search(r'connection from', line, re.IGNORECASE)

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

    return log_entry
        
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
    diag = {}
    #server_unresponsive = {}
    #server_unresponsive["severity"] = "Normal"
    #server_unresponsive["count"] = 0
    #server_unresponsive["timematch"] = ""
    #diag["server_unresponsive"] = server_unresponsive
    results = {}
    
    # Extract data
    for entry in entries:
        parsed = parse_log_entry(entry['content'], diag, results)
        if re.search(r'conn=488 op=3 BIND', entry['content'], re.IGNORECASE):
            #pdb.set_trace()
            pass
        continue
        severities[parsed.get('severity', 'UNKNOWN')] += 1
        
        if 'component' in parsed:
            components[parsed['component']] += 1
            if parsed.get('severity') in ['ERROR', 'CRITICAL', 'FATAL']:
                errors_by_component[parsed['component']].append(parsed.get('message', ''))
        
        if 'timestamp' in parsed:
            timestamps.append(parsed['timestamp'])
    return results
    
    #pdb.set_trace()
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
    #pdb.set_trace()
    solutions = []
    server_unresponsive = analysis["server_unresponsive"]
    abandon_too_late = analysis["abandon_too_late"]
    abandon_high_etime = analysis["abandon_high_etime"]
    for event in server_unresponsive["event_unresponsive"]:
        if str(event["severity"]) == "fatal":
            solutions.append({
                'problem': 'Around %s the server was completely unresponsive and unable to process new requests.' % event["timematch"],
                'solution': 'As an immediate relief you should increase the number of worker threads. If you can correlate the problem with a long update then you can tune some sensitive plugins (memberof, automember, referential integrity) known to impact others threads.',
                'root cause': 'A reason can be that current requests are long. Other reason can be a specific task (update) that blocked all the others requests',
                'further investigations': 'Compare the long operations (etime) with similar operations before/after to confirm if they were also long. Check if an update (ADD/DEL/MODRDN/MOD) was started before that event and complete around the same time that the others requests returned their result. Check if the unresponsiveness was transient or if was a kind of fatal deadlock. Need to collect `top -H` and periodic `pstack`'
        })
        else:
            if event["severity"] == "critical":
                solutions.append({
                    'problem': 'Around %s the server was transiantly unresponsive and unable to process new requests.' % event["timematch"],
                    'solution': 'As an immediate relief you should increase the number of worker threads.',
                    'root cause': 'A reason can be that current requests are long. Other reason can be a specific update was impacting others requests',
                    'further investigations': 'Check the update operations started just before %s, if one of them was a bit long (using `etime`).' % event["timematch"]
                })
            else:
                if event["severity"] == "warning":
                    solutions.append({
                        'problem': 'Around %s the server was possibly unresponsive for a short period of time.' % event["timematch"],
                        'solution': 'As an immediate relief you should increase the number of worker threads.',
                        'root cause': 'A reason can be that current requests are long. Other reason can be a specific update was impacting others requests',
                        'further investigations': 'Check the update operations started just before %s, if one of them was a bit long (using `etime`).' % event["timematch"]
                    })
    for event in abandon_too_late["event_abandon_too_late"]:
        global_desc = {
                'solution': 'As an immediate relief you should increase the number of worker threads. If you can correlate the problem with a long update then you can tune some sensitive plugins (memberof, automember, referential integrity) known to impact others threads.',
                'root cause': 'A reason can be that the server was suffering of worker threads starvation, because current requests are long or blocked by a specific update. Another reason can be that the clients, badly designed, were not reading the results of their requests. Another reason can be that the clients sent too many asynchronous requests and the server did not read new requests while the clients believed it was reading them',
                'further investigations': 'Compare the long operations (etime) with similar operations before/after to confirm if they were also long. Check if an update (ADD/DEL/MODRDN/MOD) was started before that event and complete around the same time that the others requests returned their result. Check if the unresponsiveness was transient or if was a kind of fatal deadlock. Need to collect `top -H` and periodic `pstack`. Check, with cn=monitor, if there was a spike of connections hitting the maximum threads per connection (default is 5). Check if the abandonned operations (likely the ones before abandonned) was waiting for long in the waiting queue (wtime) or were slow to proceed (etime).'
                }
        if str(event["severity"]) == "fatal":
            global_desc['problem'] = 'Around %s clients massively abandonned requests that were arleady processed.' % event["timematch"]
        else:
            if event["severity"] == "critical":
                global_desc['problem'] = 'Around %s several clients abandonned requests that were arleady processed.' % event["timematch"]
            else:
                if event["severity"] == "warning":
                    global_desc['problem'] = 'Around %s few clients abandonned requests that were arleady processed.' % event["timematch"]
        solutions.append(global_desc)

    for event in abandon_high_etime["event_abandon_high_etime"]:
        global_desc = {
                'solution': 'If you can correlate the problem with a long update then you can tune some sensitive plugins (memberof, automember, referential integrity) known to impact others threads. Another possibility is to index some attribute because some requests trigger unindexed searches.',
                'root cause': 'Current requests are long or blocked by a specific update. Another reason can be that the clients are expecting too fast response time for the abandonned requests.',
                'further investigations': 'Check if an update (ADD/DEL/MODRDN/MOD) was started before that event and could impact others request like holding the same backend. Check if the unresponsiveness was transient or if was a kind of fatal deadlock. Need to collect `top -H` and periodic `pstack`. Check if the abandonned operations (likely the ones before abandonned) was waiting for long in the waiting queue (wtime) or were slow to proceed (etime).'
                }
        if str(event["severity"]) == "fatal":
            global_desc['problem'] = 'Around %s clients massively abandonned requests that were running for long time.' % event["timematch"]
        else:
            if event["severity"] == "critical":
                global_desc['problem'] = 'Around %s several clients abandonned requests that were running for long time.' % event["timematch"]
            else:
                if event["severity"] == "warning":
                    global_desc['problem'] = 'Around %s few clients abandonned requests that were running for long time.' % event["timematch"]
        solutions.append(global_desc)

    return solutions
    for event in server_unresponsive["event_unresponsive"]:
        if str(event["severity"]) == "fatal":
            solutions.append({
                'problem': 'Server completely unresponsive: The servers is no longer able to process new requests.',
                'when': event['timematch'],
                'explanations': ['A reason can be that current requests are long',
                                 'A reason can be a specific task (update) that blocked all the others requests',
                                 ],
                'solutions': ['As an immediate relief you should increase the number of worker threads',
                              'If correlated to long update, you may tune some sensitive plugins (memberof, automember, referential integrity)'
                              ],
                'further investigations': ['Compare the long operations (etime) with similar operations before/after to confirm if they were also long',
                                           'Check if an update (ADD/DEL/MODRDN/MOD) was started before that event and complete around the same time that the others requests returned their result',
                                           'Check if the unresponsiveness was transient or if was a kind of fatal deadlock',
                                           'Need to collect `top -H` and periodic `pstack`',
                                           ],
                })

    return solutions
    
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
    parser.add_argument("--solution-len", type=str, default="10", help="length of displayed solution")
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
    matches = search_files_for_term(log_files, args.term, max_matches=1000000)
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
#        'matches': matches,
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
        
        if 'severity_distribution' in analysis:
            print("\nSeverity distribution:")
            for severity, count in analysis['severity_distribution'].items():
                print(f"  - {severity}: {count}")
        
        #pdb.set_trace()
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
                #pdb.set_trace()
                print(f"  {i}. {problem}")
                
                # Debug the content of the solution
                if os.getenv("DEBUG") == "1":
                    print(f"DEBUG: Solution {i} content length: {len(solution_text)}")
                    print(f"DEBUG: Solution {i} first 50 chars: {solution_text[:50]}...")
                
                # Only display the first 3-4 lines of the enhanced solution to keep it concise
                # Split by newlines and filter out empty lines
                solution_lines = [line for line in solution_text.split('\n') if line.strip()]
                solution_len = int(args.solution_len)
                if len(solution_lines) > solution_len:
                    # Display first 10 lines if the solution is very long
                    display_solution = '\n     '.join(solution_lines[:solution_len]) + '\n     ...'
                else:
                    display_solution = '\n     '.join(solution_lines)
                
                print(f"     {display_solution}")
                
                # Add a line break for readability
                if i < len(ai_enhanced_solutions):
                    print("\n\n")
        
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
