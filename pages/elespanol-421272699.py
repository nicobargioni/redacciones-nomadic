"""
Dashboard de El Español - Cliente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages._dashboard_template import render_dashboard

# Configuración del dashboard
CONFIG = {
    'medio': 'elespanol',
    'page_type': 'cliente',
    'page_title': 'Dashboard El Español - Cliente',
    'page_icon': '🇪🇸',
    'monthly_goal': 3000000,  # 3 millones de Page Views
}

# Renderizar dashboard
render_dashboard(CONFIG)
