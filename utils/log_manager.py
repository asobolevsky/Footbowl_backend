import os
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import Config
from utils.logging_config import get_logger


class LogManager:
    """Manages log rotation, compression, and cleanup"""
    
    def __init__(self):
        self.logs_dir = Path(Config.LOGS_DIR)
        self.logger = get_logger('log_manager')
        self.retention_days = int(os.getenv('LOG_RETENTION_DAYS', '30'))
        self.max_file_size = int(Config.LOG_FILE_MAX_BYTES)
        self.backup_count = int(Config.LOG_FILE_BACKUP_COUNT)
    
    def compress_old_logs(self):
        """Compress log files older than 1 day"""
        self.logger.info("Starting log compression...")
        
        compressed_count = 0
        for log_file in self.logs_dir.glob("*.log.*"):
            if not log_file.name.endswith('.gz'):
                try:
                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original file
                    log_file.unlink()
                    compressed_count += 1
                    self.logger.debug(f"Compressed: {log_file}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to compress {log_file}: {e}")
        
        self.logger.info(f"Log compression completed. Compressed {compressed_count} files.")
        return compressed_count
    
    def cleanup_old_logs(self):
        """Remove log files older than retention period"""
        self.logger.info(f"Starting log cleanup (retention: {self.retention_days} days)...")
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        for log_file in self.logs_dir.glob("*.log*"):
            try:
                # Get file modification time
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Removed old log: {log_file}")
                    
            except Exception as e:
                self.logger.error(f"Failed to remove {log_file}: {e}")
        
        self.logger.info(f"Log cleanup completed. Removed {removed_count} files.")
        return removed_count
    
    def get_log_stats(self):
        """Get statistics about log files"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'files_by_type': {},
            'oldest_file': None,
            'newest_file': None
        }
        
        for log_file in self.logs_dir.glob("*.log*"):
            try:
                file_size = log_file.stat().st_size
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                stats['total_files'] += 1
                stats['total_size'] += file_size
                
                # Categorize by file type
                if log_file.name.startswith('app.log'):
                    file_type = 'application'
                elif log_file.name.startswith('access.log'):
                    file_type = 'access'
                elif log_file.name.startswith('error.log'):
                    file_type = 'error'
                else:
                    file_type = 'other'
                
                if file_type not in stats['files_by_type']:
                    stats['files_by_type'][file_type] = {'count': 0, 'size': 0}
                
                stats['files_by_type'][file_type]['count'] += 1
                stats['files_by_type'][file_type]['size'] += file_size
                
                # Track oldest and newest files
                if stats['oldest_file'] is None or file_mtime < stats['oldest_file']:
                    stats['oldest_file'] = file_mtime
                if stats['newest_file'] is None or file_mtime > stats['newest_file']:
                    stats['newest_file'] = file_mtime
                    
            except Exception as e:
                self.logger.error(f"Failed to get stats for {log_file}: {e}")
        
        return stats
    
    def rotate_logs(self):
        """Manually rotate current log files"""
        self.logger.info("Starting manual log rotation...")
        
        rotated_count = 0
        for log_file in self.logs_dir.glob("*.log"):
            if not log_file.name.endswith('.log.1'):
                try:
                    # Create backup name with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"{log_file.stem}_{timestamp}.log"
                    backup_path = log_file.parent / backup_name
                    
                    # Move current log to backup
                    shutil.move(str(log_file), str(backup_path))
                    rotated_count += 1
                    self.logger.info(f"Rotated: {log_file} -> {backup_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to rotate {log_file}: {e}")
        
        self.logger.info(f"Manual log rotation completed. Rotated {rotated_count} files.")
        return rotated_count
    
    def cleanup_empty_logs(self):
        """Remove empty log files"""
        self.logger.info("Starting cleanup of empty log files...")
        
        removed_count = 0
        for log_file in self.logs_dir.glob("*.log*"):
            try:
                if log_file.stat().st_size == 0:
                    log_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Removed empty file: {log_file}")
                    
            except Exception as e:
                self.logger.error(f"Failed to remove empty file {log_file}: {e}")
        
        self.logger.info(f"Empty log cleanup completed. Removed {removed_count} files.")
        return removed_count
    
    def run_maintenance(self):
        """Run complete log maintenance routine"""
        self.logger.info("Starting log maintenance routine...")
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)
        
        # Get initial stats
        initial_stats = self.get_log_stats()
        self.logger.info(f"Initial log stats: {initial_stats}")
        
        # Run maintenance tasks
        compressed = self.compress_old_logs()
        removed = self.cleanup_old_logs()
        empty_removed = self.cleanup_empty_logs()
        
        # Get final stats
        final_stats = self.get_log_stats()
        
        # Log summary
        self.logger.info(
            f"Log maintenance completed - "
            f"Compressed: {compressed}, Removed: {removed}, Empty removed: {empty_removed}, "
            f"Final files: {final_stats['total_files']}, "
            f"Final size: {self._format_size(final_stats['total_size'])}"
        )
        
        return {
            'compressed': compressed,
            'removed': removed,
            'empty_removed': empty_removed,
            'initial_stats': initial_stats,
            'final_stats': final_stats
        }
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"


def setup_log_rotation_schedule():
    """Setup automatic log rotation schedule"""
    import schedule
    import time
    from threading import Thread
    
    log_manager = LogManager()
    
    def run_maintenance():
        """Run maintenance in a separate thread"""
        try:
            log_manager.run_maintenance()
        except Exception as e:
            logger = get_logger('log_manager')
            logger.error(f"Log maintenance failed: {e}")
    
    # Schedule maintenance tasks
    schedule.every().day.at("02:00").do(run_maintenance)  # Daily at 2 AM
    schedule.every().week.do(run_maintenance)  # Weekly full maintenance
    
    def maintenance_worker():
        """Background worker for scheduled maintenance"""
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Check every hour
    
    # Start maintenance worker in background
    maintenance_thread = Thread(target=maintenance_worker, daemon=True)
    maintenance_thread.start()
    
    logger = get_logger('log_manager')
    logger.info("Log rotation schedule started - Daily at 2 AM, Weekly full maintenance")


# CLI interface for log management
if __name__ == "__main__":
    import sys
    
    log_manager = LogManager()
    
    if len(sys.argv) < 2:
        print("Usage: python log_manager.py [compress|cleanup|rotate|stats|maintenance]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "compress":
        count = log_manager.compress_old_logs()
        print(f"Compressed {count} log files")
    
    elif command == "cleanup":
        count = log_manager.cleanup_old_logs()
        print(f"Removed {count} old log files")
    
    elif command == "rotate":
        count = log_manager.rotate_logs()
        print(f"Rotated {count} log files")
    
    elif command == "stats":
        stats = log_manager.get_log_stats()
        print(f"Log Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size: {log_manager._format_size(stats['total_size'])}")
        print(f"  Files by type: {stats['files_by_type']}")
        print(f"  Oldest file: {stats['oldest_file']}")
        print(f"  Newest file: {stats['newest_file']}")
    
    elif command == "maintenance":
        result = log_manager.run_maintenance()
        print(f"Maintenance completed: {result}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
