import subprocess
import re
import os
from pathlib import Path
from datetime import datetime

class ArchiveContentViewer:
    """View archive contents without extracting using WinRAR"""
    
    def __init__(self, winrar_path=None):
        self.winrar_path = winrar_path or self._find_winrar()
        
    def _find_winrar(self):
        """Find WinRAR executable"""
        common_paths = [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
            r"C:\WinRAR\WinRAR.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(['where', 'WinRAR'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def get_archive_contents(self, archive_path):
        """Get archive contents without extracting"""
        if not self.winrar_path:
            return {'success': False, 'error': 'WinRAR not found'}
        
        if not os.path.exists(archive_path):
            return {'success': False, 'error': 'Archive file not found'}
        
        try:
            # Use WinRAR to list contents
            cmd = [self.winrar_path, 'l', '-y', archive_path]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                return self._parse_winrar_output(result.stdout)
            else:
                return {'success': False, 'error': f'WinRAR error: {result.stderr}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Error reading archive: {str(e)}'}
    
    def _parse_winrar_output(self, output):
        """Parse WinRAR listing output"""
        try:
            lines = output.split('\n')
            files = []
            total_size = 0
            file_count = 0
            
            # Find the start of the file list
            start_index = -1
            for i, line in enumerate(lines):
                if '------------------- ----- ------------ ------------  ------------------------' in line:
                    start_index = i + 1
                    break
            
            if start_index == -1:
                return {'success': False, 'error': 'Could not parse archive contents - no file list found'}
            
            # Parse file entries
            for line in lines[start_index:]:
                if not line.strip() or line.startswith('---'):
                    continue
                
                # Skip summary lines
                if line.strip().startswith('---') or 'files' in line.lower() or 'folders' in line.lower():
                    continue
                    
                # WinRAR format: Name    Size    Packed    Ratio    Date    Time    Attr    CRC    Ver
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        # Extract file info
                        name = ' '.join(parts[:-6])  # File name (may contain spaces)
                        size_str = parts[-6].replace(',', '').replace('i', '')  # Remove 'i' and commas
                        size = int(size_str) if size_str.isdigit() else 0  # File size
                        packed = int(parts[-5].replace(',', ''))  # Packed size
                        ratio = parts[-4]  # Compression ratio
                        date = parts[-3]  # Date
                        time = parts[-2]  # Time
                        attrs = parts[-1]  # Attributes
                        
                        # Determine file type from attributes
                        file_type = 'file'
                        if attrs.startswith('D'):
                            file_type = 'directory'
                        elif name.endswith('/'):
                            file_type = 'directory'
                        
                        files.append({
                            'name': name,
                            'size': size,
                            'packed': packed,
                            'ratio': ratio,
                            'date': date,
                            'time': time,
                            'attrs': attrs,
                            'type': file_type
                        })
                        
                        total_size += size
                        file_count += 1
                        
                    except (ValueError, IndexError) as e:
                        # Skip malformed lines
                        continue
            
            return {
                'success': True,
                'files': files,
                'total_size': total_size,
                'file_count': file_count
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Error parsing archive contents: {str(e)}'}
    
    def _extract_archive_info(self, lines):
        """Extract archive information from header"""
        info = {}
        
        for line in lines:
            if 'Archive:' in line:
                info['archive_name'] = line.split('Archive:')[1].strip()
            elif 'Size:' in line:
                info['archive_size'] = line.split('Size:')[1].strip()
            elif 'Created:' in line:
                info['created'] = line.split('Created:')[1].strip()
            elif 'Attributes:' in line:
                info['attributes'] = line.split('Attributes:')[1].strip()
        
        return info
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def get_file_tree(self, archive_path):
        """Get files organized in tree structure"""
        contents = self.get_archive_contents(archive_path)
        
        if not contents['success']:
            return contents
        
        tree = {}
        
        for file_info in contents['files']:
            path_parts = file_info['name'].split('/')
            current_level = tree
            
            for i, part in enumerate(path_parts):
                if part == '':
                    continue
                    
                if i == len(path_parts) - 1 and file_info['type'] == 'file':
                    # This is a file
                    current_level[part] = {
                        'type': 'file',
                        'size': file_info['size'],
                        'info': file_info
                    }
                else:
                    # This is a directory
                    if part not in current_level:
                        current_level[part] = {
                            'type': 'directory',
                            'children': {}
                        }
                    current_level = current_level[part]['children']
        
        return {
            'success': True,
            'tree': tree,
            'archive_info': contents['archive_info'],
            'total_files': contents['total_files'],
            'total_size': contents['total_size']
        }


# Test function
def test_archive_viewer():
    """Test the archive content viewer"""
    viewer = ArchiveContentViewer()
    
    if not viewer.winrar_path:
        print("WinRAR not found")
        return
    
    print(f"Using WinRAR: {viewer.winrar_path}")
    
    # Test with a sample archive (you would replace this with actual archive path)
    test_archive = "test.rar"  # Replace with actual archive path
    
    if os.path.exists(test_archive):
        print(f"\nTesting with: {test_archive}")
        
        # Get basic contents
        contents = viewer.get_archive_contents(test_archive)
        
        if contents['success']:
            print(f"Total files: {contents['total_files']}")
            print(f"Total size: {viewer.format_size(contents['total_size'])}")
            print("\nFiles:")
            for file_info in contents['files'][:10]:  # Show first 10 files
                size_str = viewer.format_size(file_info['size'])
                type_icon = "📁" if file_info['type'] == 'directory' else "📄"
                print(f"{type_icon} {file_info['name']} ({size_str})")
            
            if len(contents['files']) > 10:
                print(f"... and {len(contents['files']) - 10} more files")
        else:
            print(f"Error: {contents['error']}")
    else:
        print(f"Test archive not found: {test_archive}")


if __name__ == "__main__":
    test_archive_viewer()
