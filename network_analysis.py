from datetime import datetime
import json


class NetworkMetrics:
    def __init__(self):
        self.data_transfer_log = []

    def log_transfer(self, action, filename, size_bytes, time_seconds, speed_mbps):
        self.data_transfer_log.append({
            'timestamp': datetime.now().isoformat(),
            'action_type': action,
            'file_name': filename,
            'file_size_bytes': size_bytes,
            'time_taken_seconds': time_seconds,
            'transfer_rate_mbps': speed_mbps
        })

    # Export logs as JSON for convenient offline review
    def export_logs(self, output_file='network_metrics.json'):
        with open(output_file, 'w') as outfile:
            json.dump(self.data_transfer_log, outfile, indent=2)

