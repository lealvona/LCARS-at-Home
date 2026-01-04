#!/usr/bin/env python3
"""
LCARS Computer - Configuration Backup Utility

This script creates comprehensive backups of all LCARS Computer configuration
files, including Home Assistant, n8n workflows, and Docker settings. Backups
are essential for disaster recovery and migration between systems.

The backup process captures:
  - Home Assistant configuration files
  - n8n workflow exports
  - Docker Compose and environment files
  - ESPHome device configurations
  - Custom prompts and documentation

Usage:
    python3 backup.py [options]

Options:
    --output DIR    Directory to store backups (default: ./backups)
    --compress      Create a compressed archive (tar.gz)
    --encrypt       Encrypt the backup with a password
    --upload S3     Upload to S3-compatible storage
    --keep N        Number of backups to retain (default: 10)
    --verbose       Show detailed progress
    --help          Show this help message

Examples:
    # Basic backup to default location
    python3 backup.py

    # Compressed backup with custom output directory
    python3 backup.py --output /mnt/backup --compress

    # Encrypted backup with retention policy
    python3 backup.py --compress --encrypt --keep 5
"""

import os
import sys
import json
import shutil
import hashlib
import tarfile
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Attempt to import optional dependencies. These enhance functionality but
# are not strictly required for basic backup operations.
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class BackupManager:
    """
    Manages the backup process for the LCARS Computer system.
    
    This class coordinates the collection of configuration files from various
    sources, creates a structured backup directory, and optionally compresses
    and encrypts the result.
    
    Attributes:
        project_dir: Root directory of the LCARS Computer installation
        output_dir: Directory where backups will be stored
        verbose: Whether to print detailed progress information
    """
    
    def __init__(self, project_dir: Path, output_dir: Path, verbose: bool = False):
        """
        Initialize the backup manager.
        
        Args:
            project_dir: Path to the LCARS Computer project root
            output_dir: Path where backups should be stored
            verbose: Enable verbose output
        """
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.verbose = verbose
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_name = f"lcars_backup_{self.timestamp}"
        self.backup_path = self.output_dir / self.backup_name
        
        # Define the files and directories to back up. This mapping associates
        # source paths with their destination in the backup structure.
        self.backup_sources = {
            'homeassistant': [
                'homeassistant/config/configuration.yaml',
                'homeassistant/config/automations.yaml',
                'homeassistant/config/scripts.yaml',
                'homeassistant/config/scenes.yaml',
                'homeassistant/config/groups.yaml',
                'homeassistant/config/customize.yaml',
                'homeassistant/config/extended_openai.yaml',
            ],
            'n8n': [
                'n8n/workflows/',
            ],
            'docker': [
                'docker/docker-compose.yml',
                'docker/docker-compose.gpu.yml',
                'docker/.env',
            ],
            'esphome': [
                'esphome/',
            ],
            'prompts': [
                'prompts/',
            ],
            'scripts': [
                'scripts/',
            ],
        }
    
    def log(self, message: str, level: str = 'INFO'):
        """Print a log message if verbose mode is enabled or level is ERROR."""
        if self.verbose or level == 'ERROR':
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{level}] {message}")
    
    def create_backup_directory(self) -> Path:
        """
        Create the backup directory structure.
        
        The backup directory mirrors the project structure, making it easy
        to understand what's included and to restore individual components.
        
        Returns:
            Path to the created backup directory
        """
        self.log(f"Creating backup directory: {self.backup_path}")
        
        # Create the main backup directory and subdirectories
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        for category in self.backup_sources.keys():
            (self.backup_path / category).mkdir(exist_ok=True)
        
        return self.backup_path
    
    def copy_files(self) -> dict:
        """
        Copy all configuration files to the backup directory.
        
        This method iterates through the backup sources, copying each file
        or directory to the appropriate location in the backup structure.
        It handles missing files gracefully, logging warnings rather than
        failing the entire backup.
        
        Returns:
            Dictionary containing backup statistics
        """
        stats = {
            'files_copied': 0,
            'files_skipped': 0,
            'bytes_copied': 0,
            'errors': []
        }
        
        for category, paths in self.backup_sources.items():
            self.log(f"Backing up {category}...")
            
            for rel_path in paths:
                source = self.project_dir / rel_path
                dest = self.backup_path / category / Path(rel_path).name
                
                try:
                    if source.is_dir():
                        # Copy entire directory tree
                        if source.exists():
                            shutil.copytree(source, dest, dirs_exist_ok=True)
                            # Count files in the directory
                            for f in source.rglob('*'):
                                if f.is_file():
                                    stats['files_copied'] += 1
                                    stats['bytes_copied'] += f.stat().st_size
                            self.log(f"  Copied directory: {rel_path}")
                        else:
                            self.log(f"  Skipped (not found): {rel_path}", 'WARN')
                            stats['files_skipped'] += 1
                    else:
                        # Copy individual file
                        if source.exists():
                            shutil.copy2(source, dest)
                            stats['files_copied'] += 1
                            stats['bytes_copied'] += source.stat().st_size
                            self.log(f"  Copied file: {rel_path}")
                        else:
                            self.log(f"  Skipped (not found): {rel_path}", 'WARN')
                            stats['files_skipped'] += 1
                            
                except Exception as e:
                    self.log(f"  Error copying {rel_path}: {e}", 'ERROR')
                    stats['errors'].append(str(e))
        
        return stats
    
    def export_n8n_workflows(self) -> bool:
        """
        Export workflows directly from n8n API if available.
        
        This method attempts to connect to the n8n API to export the current
        state of all workflows. This captures any changes made through the
        n8n UI that aren't reflected in the JSON files on disk.
        
        Returns:
            True if export was successful, False otherwise
        """
        if not REQUESTS_AVAILABLE:
            self.log("Requests library not available, skipping n8n API export", 'WARN')
            return False
        
        try:
            # Try to connect to n8n API (assumes default local setup)
            response = requests.get(
                'http://localhost:5678/api/v1/workflows',
                timeout=10
            )
            
            if response.status_code == 200:
                workflows = response.json()
                export_dir = self.backup_path / 'n8n' / 'api_export'
                export_dir.mkdir(exist_ok=True)
                
                for workflow in workflows.get('data', []):
                    workflow_name = workflow.get('name', 'unnamed').replace(' ', '_')
                    workflow_file = export_dir / f"{workflow_name}.json"
                    
                    with open(workflow_file, 'w') as f:
                        json.dump(workflow, f, indent=2)
                    
                    self.log(f"  Exported workflow: {workflow_name}")
                
                return True
            else:
                self.log(f"n8n API returned status {response.status_code}", 'WARN')
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Could not connect to n8n API: {e}", 'WARN')
            return False
    
    def create_manifest(self, stats: dict) -> Path:
        """
        Create a manifest file describing the backup contents.
        
        The manifest provides metadata about the backup, including timestamps,
        file counts, and checksums for verification purposes.
        
        Args:
            stats: Dictionary containing backup statistics
        
        Returns:
            Path to the created manifest file
        """
        manifest = {
            'backup_name': self.backup_name,
            'created_at': datetime.now().isoformat(),
            'lcars_version': '1.0.0',
            'statistics': stats,
            'contents': {},
            'checksums': {}
        }
        
        # List all files in the backup with their checksums
        for file_path in self.backup_path.rglob('*'):
            if file_path.is_file() and file_path.name != 'manifest.json':
                rel_path = str(file_path.relative_to(self.backup_path))
                
                # Calculate MD5 checksum for verification
                with open(file_path, 'rb') as f:
                    checksum = hashlib.md5(f.read()).hexdigest()
                
                manifest['checksums'][rel_path] = checksum
        
        manifest['contents'] = list(manifest['checksums'].keys())
        
        # Write manifest to the backup directory
        manifest_path = self.backup_path / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        self.log(f"Created manifest with {len(manifest['contents'])} files")
        return manifest_path
    
    def compress_backup(self) -> Path:
        """
        Compress the backup directory into a tar.gz archive.
        
        Compression significantly reduces backup size and makes the backup
        easier to transfer or store. The original directory is removed
        after successful compression.
        
        Returns:
            Path to the compressed archive
        """
        archive_path = self.backup_path.with_suffix('.tar.gz')
        
        self.log(f"Compressing backup to {archive_path.name}...")
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(self.backup_path, arcname=self.backup_name)
        
        # Calculate compression ratio
        original_size = sum(
            f.stat().st_size for f in self.backup_path.rglob('*') if f.is_file()
        )
        compressed_size = archive_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        self.log(f"Compression complete: {compressed_size / 1024 / 1024:.1f}MB ({ratio:.1f}% reduction)")
        
        # Remove the uncompressed directory
        shutil.rmtree(self.backup_path)
        
        return archive_path
    
    def encrypt_backup(self, archive_path: Path, password: str) -> Path:
        """
        Encrypt the backup archive using GPG symmetric encryption.
        
        Encryption protects sensitive configuration data (API keys, passwords)
        if the backup is stored in an untrusted location.
        
        Args:
            archive_path: Path to the archive to encrypt
            password: Encryption password
        
        Returns:
            Path to the encrypted file
        """
        encrypted_path = archive_path.with_suffix('.tar.gz.gpg')
        
        self.log("Encrypting backup...")
        
        try:
            subprocess.run(
                [
                    'gpg', '--symmetric', '--cipher-algo', 'AES256',
                    '--batch', '--yes', '--passphrase', password,
                    '--output', str(encrypted_path),
                    str(archive_path)
                ],
                check=True,
                capture_output=True
            )
            
            # Remove the unencrypted archive
            archive_path.unlink()
            
            self.log("Encryption complete")
            return encrypted_path
            
        except subprocess.CalledProcessError as e:
            self.log(f"Encryption failed: {e}", 'ERROR')
            return archive_path
        except FileNotFoundError:
            self.log("GPG not found. Install gnupg for encryption support.", 'WARN')
            return archive_path
    
    def cleanup_old_backups(self, keep: int):
        """
        Remove old backups, keeping only the most recent N backups.
        
        This prevents backup storage from growing indefinitely while ensuring
        that recent backups are always available.
        
        Args:
            keep: Number of backups to retain
        """
        self.log(f"Cleaning up old backups (keeping {keep})...")
        
        # Find all backup files
        backup_files = sorted(
            self.output_dir.glob('lcars_backup_*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove backups beyond the retention limit
        for old_backup in backup_files[keep:]:
            if old_backup.is_dir():
                shutil.rmtree(old_backup)
            else:
                old_backup.unlink()
            self.log(f"  Removed old backup: {old_backup.name}")
    
    def run(self, compress: bool = False, encrypt_password: Optional[str] = None,
            keep: Optional[int] = None) -> Path:
        """
        Execute the complete backup process.
        
        This is the main entry point for creating a backup. It orchestrates
        all backup steps and returns the path to the final backup artifact.
        
        Args:
            compress: Whether to compress the backup
            encrypt_password: Password for encryption (None to skip)
            keep: Number of backups to retain (None to skip cleanup)
        
        Returns:
            Path to the final backup file or directory
        """
        print(f"\n{'='*60}")
        print("         LCARS COMPUTER BACKUP UTILITY")
        print(f"{'='*60}\n")
        
        # Create backup directory structure
        self.create_backup_directory()
        
        # Copy configuration files
        stats = self.copy_files()
        
        # Try to export workflows from n8n API
        self.export_n8n_workflows()
        
        # Create manifest
        self.create_manifest(stats)
        
        # Determine the final backup path
        final_path = self.backup_path
        
        # Compress if requested
        if compress:
            final_path = self.compress_backup()
        
        # Encrypt if password provided
        if encrypt_password:
            final_path = self.encrypt_backup(final_path, encrypt_password)
        
        # Clean up old backups
        if keep is not None:
            self.cleanup_old_backups(keep)
        
        # Print summary
        print(f"\n{'='*60}")
        print("                 BACKUP COMPLETE")
        print(f"{'='*60}")
        print(f"\nBackup location: {final_path}")
        print(f"Files backed up: {stats['files_copied']}")
        print(f"Files skipped:   {stats['files_skipped']}")
        print(f"Total size:      {stats['bytes_copied'] / 1024 / 1024:.1f} MB")
        
        if stats['errors']:
            print(f"\nWarning: {len(stats['errors'])} errors occurred during backup.")
        
        print()
        
        return final_path


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='LCARS Computer Configuration Backup Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--output', '-o', type=Path,
                        default=Path('./backups'),
                        help='Directory to store backups')
    parser.add_argument('--compress', '-c', action='store_true',
                        help='Create compressed archive')
    parser.add_argument('--encrypt', '-e', action='store_true',
                        help='Encrypt the backup (will prompt for password)')
    parser.add_argument('--keep', '-k', type=int, default=None,
                        help='Number of backups to retain')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed progress')
    
    args = parser.parse_args()
    
    # Determine project directory (parent of scripts directory)
    script_dir = Path(__file__).parent.resolve()
    project_dir = script_dir.parent
    
    # Create output directory if it doesn't exist
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Get encryption password if requested
    encrypt_password = None
    if args.encrypt:
        import getpass
        encrypt_password = getpass.getpass("Enter encryption password: ")
        confirm = getpass.getpass("Confirm password: ")
        if encrypt_password != confirm:
            print("Passwords do not match. Aborting.")
            sys.exit(1)
    
    # Run backup
    manager = BackupManager(project_dir, args.output, args.verbose)
    backup_path = manager.run(
        compress=args.compress,
        encrypt_password=encrypt_password,
        keep=args.keep
    )
    
    sys.exit(0)


if __name__ == '__main__':
    main()
