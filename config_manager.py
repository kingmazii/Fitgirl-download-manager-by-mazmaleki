import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

def get_config_path():
    """Get the config file path next to the exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys.executable).parent
    else:
        # Running as script
        base_path = Path(__file__).parent
    
    return base_path / "config.json"

def load_config():
    """Load configuration from config file"""
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_config(config):
    """Save configuration to config file"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

def get_setting(key, default=None):
    """Get a specific setting from config"""
    config = load_config()
    return config.get(key, default)

def set_setting(key, value):
    """Set a specific setting in config"""
    config = load_config()
    config[key] = value
    return save_config(config)

# URL Tracking Functions
def get_url_tracking():
    """Get URL tracking data from config"""
    config = load_config()
    return config.get('url_tracking', {
        'imported_urls': [],  # List of all imported URLs
        'downloaded_urls': [],  # List of successfully downloaded URLs
        'url_to_filename': {},  # Map URL to actual filename
        'archive_groups': {}  # Groups of sequential archives
    })

def save_url_tracking(url_tracking):
    """Save URL tracking data to config"""
    config = load_config()
    config['url_tracking'] = url_tracking
    return save_config(config)

def add_imported_urls(urls: List[str], url_to_filename: Dict[str, str] = None, total_available_links: int = None):
    """Add imported URLs to tracking with optional total available links from fetch"""
    from datetime import datetime
    
    tracking = get_url_tracking()
    
    # Clear existing URL tracking when importing new URLs
    tracking['imported_urls'] = []
    tracking['downloaded_urls'] = []
    tracking['url_to_filename'] = {}
    tracking['archive_groups'] = {}
    
    # Store total available links if provided (from fetch mechanism)
    if total_available_links is not None:
        tracking['total_available_links'] = total_available_links
        print(f"DEBUG: Storing fetch total: {total_available_links} links")
    
    # Use provided filename mapping or create from URLs
    if url_to_filename is None:
        url_to_filename = {}
        for url in urls:
            filename = url.split('/')[-1].split('#')[0]  # Remove hash fragment
            url_to_filename[url] = filename
    
    # Add new URLs with their filenames
    for url in urls:
        if url not in tracking['imported_urls']:
            tracking['imported_urls'].append(url)
            # Store the filename from mapping
            if url in url_to_filename:
                tracking['url_to_filename'][url] = url_to_filename[url]
    
    # Group archives by sequential pattern
    tracking['archive_groups'] = group_sequential_archives(tracking['imported_urls'], tracking['url_to_filename'])
    
    # Add date to each group for cleanup tracking
    current_date = datetime.now().isoformat()
    for group_key, group_data in tracking['archive_groups'].items():
        group_data['date_added'] = current_date
        # Store total available links for each group if available
        if total_available_links is not None:
            group_data['total_available_links'] = total_available_links
            group_data['missing_links'] = total_available_links - len(group_data['imported_parts'])
            print(f"DEBUG: Group {group_key} - Missing {group_data['missing_links']} links ({len(group_data['imported_parts'])}/{total_available_links})")
    
    # Store fetch data at bottom of config for visibility
    config = load_config()
    if 'fetch_data' not in config:
        config['fetch_data'] = {}
    
    # Store fetch summary
    config['fetch_data']['last_fetch'] = {
        'timestamp': current_date,
        'total_available_links': total_available_links,
        'imported_links': len(urls),
        'missing_links': total_available_links - len(urls) if total_available_links else 0,
        'groups': {}
    }
    
    # Store per-group fetch data
    for group_key, group_data in tracking['archive_groups'].items():
        group_name = group_data['base_name']
        config['fetch_data']['last_fetch']['groups'][group_name] = {
            'total_available': group_data.get('total_available_links', len(group_data['imported_parts'])),
            'imported': len(group_data['imported_parts']),
            'missing': group_data.get('missing_links', 0),
            'imported_parts': group_data['imported_parts']
        }
    
    save_config(config)
    save_url_tracking(tracking)
    
    # Run automatic cleanup of old groups
    cleanup_old_groups(days_old=3)

def store_fetch_data(all_links: List[Tuple[str, str]]):
    """Store all fetched links grouped by game name for accurate tracking"""
    from datetime import datetime
    import re
    
    config = load_config()
    if 'fetch_data' not in config:
        config['fetch_data'] = {}
    
    # Group all fetched links by game name
    fetch_groups = {}
    
    for text, href in all_links:
        # Extract game name and part info from filename
        filename = text.strip()
        
        # Pattern to extract base name and part number
        # Examples:
        # "fg-selective-italian.part1.rar" -> base="fg-selective-italian", part=1
        # "CoD_-_Black_Ops_3_–_fitgirl-repacks.site_–_.part01.rar" -> base="CoD_-_Black_Ops_3_–_fitgirl-repacks.site_–_", part=1
        # "fg-optional-mp.part01.rar" -> base="fg-optional-mp", part=1
        
        # Try different patterns
        patterns = [
            r'(.+?)\.part(\d+)\.(rar|zip|7z|r\d+)$',  # .part01.rar
            r'(.+?)\.(\d+)\.(rar|zip|7z|r\d+)$',       # .01.rar
        ]
        
        base_name = None
        part_num = None
        
        for pattern in patterns:
            match = re.match(pattern, filename, re.IGNORECASE)
            if match:
                base_name = match.group(1).strip()
                part_num = int(match.group(2))
                break
        
        if base_name and part_num:
            # Normalize character encoding to prevent JSON/file system mismatches
            # Convert only special Unicode dash (–) to standard double dash (--)
            base_name = base_name.replace('–', '--')
            
            if base_name not in fetch_groups:
                fetch_groups[base_name] = {
                    'total_parts': 0,
                    'parts': {},
                    'filenames': []
                }
            
            fetch_groups[base_name]['total_parts'] = max(fetch_groups[base_name]['total_parts'], part_num)
            fetch_groups[base_name]['parts'][part_num] = {
                'filename': filename,
                'href': href
            }
            fetch_groups[base_name]['filenames'].append(filename)
    
    # Store grouped fetch data
    config['fetch_data']['all_links'] = {
        'timestamp': datetime.now().isoformat(),
        'total_links': len(all_links),
        'groups': fetch_groups
    }
    
    save_config(config)
    
    # Print debug info
    print(f"DEBUG: Stored fetch data for {len(fetch_groups)} groups:")
    for group_name, group_data in fetch_groups.items():
        print(f"  {group_name}: {group_data['total_parts']} parts")
    
    return fetch_groups

def get_group_fetch_total(group_name: str) -> int:
    """Get total parts available for a specific group from fetch data"""
    config = load_config()
    fetch_data = config.get('fetch_data', {})
    
    # Check new all_links structure first
    all_links = fetch_data.get('all_links', {})
    if 'groups' in all_links and group_name in all_links['groups']:
        return all_links['groups'][group_name]['total_parts']
    
    # Fallback to last_fetch structure
    last_fetch = fetch_data.get('last_fetch', {})
    groups = last_fetch.get('groups', {})
    if group_name in groups:
        return groups[group_name].get('total_available', 0)
    
    return 0

def add_downloaded_url(url: str):
    """Mark a URL as downloaded"""
    tracking = get_url_tracking()
    
    if url not in tracking['downloaded_urls']:
        tracking['downloaded_urls'].append(url)
    
    save_url_tracking(tracking)

def group_sequential_archives(urls: List[str], url_to_filename: Dict[str, str] = None) -> Dict[str, Dict]:
    """Group URLs by sequential archive patterns"""
    groups = {}
    
    if url_to_filename is None:
        url_to_filename = {}
    
    for url in urls:
        # Get filename from mapping or extract from URL
        filename = url_to_filename.get(url, url.split('/')[-1].split('#')[0])  # Remove hash fragment
        
        # Check if it's an archive file
        if not is_archive_filename(filename):
            continue
            
        # Find the base name and part number
        group_info = extract_archive_group_info(filename)
        
        if group_info:
            base_name, part_num, total_parts = group_info
            group_key = f"{base_name}_group"
            
            if group_key not in groups:
                groups[group_key] = {
                    'base_name': base_name,
                    'total_parts': total_parts,
                    'imported_parts': [],
                    'downloaded_parts': [],
                    'urls': {},
                    'filenames': {},  # Store actual filenames
                    'is_optional': is_optional_archive(filename)
                }
            
            groups[group_key]['imported_parts'].append(part_num)
            groups[group_key]['urls'][part_num] = url
            groups[group_key]['filenames'][part_num] = filename  # Store filename
            
            # Sort parts numerically
            groups[group_key]['imported_parts'].sort()
    
    return groups

def is_archive_filename(filename: str) -> bool:
    """Check if filename is an archive file"""
    archive_extensions = ['.rar', '.zip', '.7z', '.tar', '.gz']
    return any(filename.lower().endswith(ext) for ext in archive_extensions)

def extract_archive_group_info(filename: str) -> Tuple[str, int, int]:
    """Extract base name, part number, and total parts from archive filename"""
    # Patterns for different part naming conventions
    patterns = [
        r'(.+?)\.part(\d+)\.rar$',  # .part01.rar, .part02.rar
        r'(.+?)\.part(\d+)of(\d+)\.rar$',  # .part1of5.rar
        r'(.+?)\.(\d+)\.rar$',  # .001.rar, .002.rar
        r'(.+?)\.r(\d+)$',  # .r01, .r02
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            if len(match.groups()) == 3:
                base_name, part_num, total_parts = match.groups()
                return base_name, int(part_num), int(total_parts)
            else:
                base_name, part_num = match.groups()
                # Estimate total parts from existing files
                return base_name, int(part_num), 0  # 0 means unknown
    
    return None

def is_optional_archive(filename: str) -> bool:
    """Check if archive is optional content (DLC, languages, etc.)"""
    optional_indicators = ['optional', 'dlc', 'language', 'lang', 'selective', 'bonus']
    filename_lower = filename.lower()
    return any(indicator in filename_lower for indicator in optional_indicators)

def get_archive_groups_status() -> Dict[str, Dict]:
    """Get status of all archive groups"""
    tracking = get_url_tracking()
    groups = tracking.get('archive_groups', {})
    
    # Create normalized groups mapping for compatibility
    normalized_groups = {}
    
    for group_key, group_data in groups.items():
        # Normalize character encoding for compatibility with file system names
        # Convert special Unicode dashes to standard double dashes
        normalized_key = group_key.replace('–', '--')
        normalized_base_name = group_data.get('base_name', '').replace('–', '--')
        
        # Use normalized key and base name
        normalized_group_data = group_data.copy()
        normalized_group_data['base_name'] = normalized_base_name
        
        # Check which parts are downloaded
        downloaded_parts = []
        for part_num, url in group_data['urls'].items():
            if url in tracking['downloaded_urls']:
                downloaded_parts.append(part_num)
        
        normalized_group_data['downloaded_parts'] = sorted(downloaded_parts)
        normalized_group_data['imported_count'] = len(group_data['imported_parts'])
        normalized_group_data['downloaded_count'] = len(downloaded_parts)
        
        # Calculate completion percentage
        if normalized_group_data['total_parts'] > 0:
            normalized_group_data['completion_percentage'] = (normalized_group_data['downloaded_count'] / normalized_group_data['total_parts']) * 100
            print(f"DEBUG: Group {normalized_key} - Using total_parts: {normalized_group_data['total_parts']}, downloaded_count: {normalized_group_data['downloaded_count']}, completion: {normalized_group_data['completion_percentage']}%")
        else:
            # If total parts is unknown, base on imported parts
            if normalized_group_data['imported_count'] > 0:
                normalized_group_data['completion_percentage'] = (normalized_group_data['downloaded_count'] / normalized_group_data['imported_count']) * 100
                print(f"DEBUG: Group {normalized_key} - Using imported_count: {normalized_group_data['imported_count']}, downloaded_count: {normalized_group_data['downloaded_count']}, completion: {normalized_group_data['completion_percentage']}%")
            else:
                normalized_group_data['completion_percentage'] = 0
                print(f"DEBUG: Group {normalized_key} - No counts available, completion: 0%")
        
        normalized_groups[normalized_key] = normalized_group_data
    
    return normalized_groups

def can_extract_group(group_key: str) -> Tuple[bool, str]:
    """Check if a group can be extracted (all parts downloaded)"""
    groups = get_archive_groups_status()
    
    if group_key not in groups:
        return False, "Group not found"
    
    group = groups[group_key]
    
    if group['downloaded_count'] == 0:
        return False, "No parts downloaded"
    
    if group['total_parts'] > 0:
        # We know the total parts
        if group['downloaded_count'] < group['total_parts']:
            missing = group['total_parts'] - group['downloaded_count']
            return False, f"Missing {missing} part(s) out of {group['total_parts']}"
    else:
        # Total parts unknown, check if we have at least some sequential parts
        if len(group['downloaded_parts']) < len(group['imported_parts']):
            missing = len(group['imported_parts']) - len(group['downloaded_parts'])
            return False, f"Missing {missing} imported part(s)"
    
    return True, "Ready to extract"

def get_group_filename_range(group_key: str) -> str:
    """Get a formatted string showing the filename range for a group"""
    groups = get_archive_groups_status()
    
    if group_key not in groups:
        return "Unknown group"
    
    group = groups[group_key]
    filenames = group.get('filenames', {})
    
    if not filenames:
        return "No filenames found"
    
    # Sort by part number
    sorted_parts = sorted(filenames.keys())
    
    if len(sorted_parts) == 1:
        return filenames[sorted_parts[0]]
    
    # Get first and last filenames
    first_filename = filenames[sorted_parts[0]]
    last_filename = filenames[sorted_parts[-1]]
    
    # Extract just the filename without path
    first_name = first_filename.split('/')[-1] if '/' in first_filename else first_filename
    last_name = last_filename.split('/')[-1] if '/' in last_filename else last_filename
    
    return f"{first_name} to {last_name}"

def get_group_extraction_info(group_key: str) -> Dict:
    """Get detailed extraction information for a group"""
    groups = get_archive_groups_status()
    
    if group_key not in groups:
        return {}
    
    group = groups[group_key]
    filenames = group.get('filenames', {})
    
    # Sort filenames by part number
    sorted_parts = sorted(filenames.keys())
    sorted_filenames = [filenames[part] for part in sorted_parts]
    
    return {
        'group_name': group.get('base_name', 'Unknown'),
        'filename_range': get_group_filename_range(group_key),
        'all_filenames': sorted_filenames,
        'total_parts': group.get('total_parts', len(sorted_filenames)),
        'downloaded_parts': group.get('downloaded_parts', []),
        'is_optional': group.get('is_optional', False),
        'completion_percentage': group.get('completion_percentage', 0)
    }

def clear_archive_groups():
    """Clear all archive groups data (for new session)"""
    config = load_config()
    config['archive_groups'] = {}
    save_config(config)
    print("Archive groups data cleared for new session")

def cleanup_old_groups(days_old=3):
    """Remove fully downloaded & extracted groups older than specified days"""
    from datetime import datetime, timedelta
    from pathlib import Path
    
    config = load_config()
    archive_groups = config.get('archive_groups', {})
    
    if not archive_groups:
        return  # No groups to clean
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    groups_to_remove = []
    
    for group_key, group_data in archive_groups.items():
        # Check if group is fully downloaded (100% complete)
        completion_pct = group_data.get('completion_percentage', 0)
        
        # Check if group is extracted (folder exists)
        group_name = group_data.get('base_name', group_key)
        download_dir = get_setting("download_directory", "downloads")
        extract_dest = Path(download_dir) / clean_folder_name(group_name)
        is_extracted = extract_dest.exists() and any(extract_dest.iterdir())
        
        # Get group age (use last modified date or current date if not available)
        group_date_str = group_data.get('date_added', datetime.now().isoformat())
        try:
            group_date = datetime.fromisoformat(group_date_str.replace('T', ' ').split('.')[0])
        except:
            group_date = datetime.now()  # Fallback to current date
        
        # Remove if fully downloaded, extracted, and older than cutoff
        if (completion_pct >= 100.0 and is_extracted and group_date < cutoff_date):
            groups_to_remove.append(group_key)
            print(f"Cleaning up old group: {group_name} (from {group_date.strftime('%Y-%m-%d')})")
    
    # Remove old groups
    for group_key in groups_to_remove:
        del archive_groups[group_key]
    
    if groups_to_remove:
        config['archive_groups'] = archive_groups
        save_config(config)
        print(f"Cleaned up {len(groups_to_remove)} old archive groups (older than {days_old} days)")
    else:
        print(f"No old groups to clean up (older than {days_old} days)")

def clean_folder_name(name):
    """Clean folder name by removing part numbers and common patterns"""
    import re
    
    # Remove part number patterns
    patterns = [
        r'\.part\d+',
        r'\.r\d+$',
        r'\.rar$',
    ]
    
    for pattern in patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
    return name.strip()
