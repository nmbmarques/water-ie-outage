# Water Outage Monitor

A full-stack application for monitoring and notifying about water outages across Irish counties. Features both a web interface and a command-line tool for tracking Irish Water service disruptions.

## Overview

This project provides:
- **Web Interface**: Real-time water outage viewer by county
- **Python CLI Tool**: Monitor specific counties and send email notifications when new outages occur
- **Docker Support**: Easy containerized deployment

## Features

### Web Interface
- Query water outages by Irish county
- View outage details including description, affected areas, and timelines
- Clean, responsive UI built with vanilla JavaScript and CSS
- Real-time data fetching from Irish Water ArcGIS service

### Python Monitor
- Monitor specific counties for new outages
- Email notifications for new outages
- Configurable monitoring intervals
- Persistent state tracking to identify new outages
- HTML email formatting with detailed outage information

## Project Structure

```
.
├── server.js                      # Express.js backend server
├── monitor_water_outages.py       # Python monitoring & notification script
├── package.json                   # Node.js dependencies
├── Dockerfile                     # Docker configuration
└── public/
    └── index.html                 # Frontend web interface
```

## Prerequisites

### For Web Server
- Node.js 20+ (or Docker)
- npm

### For Python Monitor
- Python 3.7+
- pip

## Installation

### Web Server Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd water-ie-notifications
```

2. Install dependencies:
```bash
npm install
```

3. Start the server:
```bash
npm start
```

The web interface will be available at `http://localhost:3000`

### Python Monitor Setup

1. Install Python dependencies:
```bash
pip install requests
```

2. (Optional) Set up a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install requests
```

## Usage

### Web Interface

Visit `http://localhost:3000` in your browser and:
1. Select a county from the dropdown
2. Click "Search" to fetch current outages
3. View detailed information about each outage

### Python Monitor

#### Basic Usage

Monitor a specific county and send email notifications:
```bash
python3 monitor_water_outages.py \
  --county "County Name" \
  --email your-email@example.com \
  --smtp-server smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-smtp-user@gmail.com \
  --smtp-password your-app-password
```

#### Command-Line Arguments

- `--county COUNTY`: Irish county to monitor (required)
- `--email EMAIL`: Email address to send notifications to (required)
- `--smtp-server SERVER`: SMTP server address (default: smtp.gmail.com)
- `--smtp-port PORT`: SMTP server port (default: 587)
- `--smtp-user USER`: SMTP login username
- `--smtp-password PASSWORD`: SMTP login password
- `--interval SECONDS`: Polling interval in seconds (default: 300)
- `--state-file FILE`: Path to state file for tracking outages (default: state.json)

#### Continuous Monitoring

To run the monitor continuously (e.g., with cron or supervisor):
```bash
python3 monitor_water_outages.py \
  --county "Dublin" \
  --email alerts@example.com \
  --smtp-user alerts@example.com \
  --smtp-password your-password
```

The script will poll every 5 minutes (default) and send an email when new outages are detected.

### Environment Variables

For security, you can set SMTP credentials via environment variables:
```bash
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
python3 monitor_water_outages.py --county "Dublin" --email alerts@example.com
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t water-outage-monitor .
```

### Run Container

```bash
docker run -p 3000:3000 water-outage-monitor
```

### Docker Compose (if available)

For production deployments with monitoring and environment variables, extend the Dockerfile as needed.

## API

The application uses the Irish Water ArcGIS REST API:
- **Endpoint**: `https://services2.arcgis.com/OqejhVam51LdtxGa/arcgis/rest/services/WaterAdvisoryCR021_DeptView/FeatureServer/0/query`

### Query Parameters

- `where`: Filter by status, county, etc.
- `f`: Response format (json)
- `outFields`: Fields to return
- `orderByFields`: Sort order

## Email Configuration

### Gmail

1. Enable 2-Factor Authentication on your Google Account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in place of your regular password

### Other SMTP Servers

Update `--smtp-server` and `--smtp-port` accordingly.

## Outage Data Format

Each outage contains:
- `OBJECTID`: Unique identifier
- `GLOBALID`: Global identifier
- `TITLE`: Outage title/reference
- `DESCRIPTION`: Detailed description (HTML formatted)
- `COUNTY`: Affected county
- `STARTDATE`: Outage start time (epoch)
- `ENDDATE`: Expected end time (epoch)
- `STATUS`: Current status (Open, Closed, etc.)
- `APPROVALSTATUS`: Approval status
- `AFFECTEDPOSTCODES`: List of affected postal codes

## Troubleshooting

### Web Server won't start
- Ensure port 3000 is not in use: `lsof -i :3000`
- Check Node.js version: `node --version`

### Python monitor not sending emails
- Verify SMTP credentials are correct
- Check firewall/antivirus blocking SMTP connections
- For Gmail, ensure App Password is used (not regular password)
- Verify email address is correct

### No outages showing
- Verify the county name matches Irish counties (case-sensitive in some queries)
- Check internet connectivity to ArcGIS service
- Try different county names

## Data Source

Data is sourced from Irish Water's ArcGIS Feature Service. The application queries real-time outage information.

## License

[Add your license here]

## Contributing

Contributions welcome! Please submit pull requests or issues.

## Support

For issues or questions, please open an issue in the repository.

