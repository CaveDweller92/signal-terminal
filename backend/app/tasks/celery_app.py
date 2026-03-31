"""
Celery application configuration (Swing Trading).

Uses Redis as both broker and result backend.
Beat schedule runs the daily pipeline automatically.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "signal_terminal",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.premarket_scan",
        "app.tasks.watchlist_build",
        "app.tasks.position_monitor",
        "app.tasks.regime_detection",
        "app.tasks.daily_meta_review",
        "app.tasks.performance_calc",
        "app.tasks.universe_update",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.conf.beat_schedule = {
    # Stock Discovery — dual screener (morning + evening)
    "premarket-scan": {
        "task": "app.tasks.premarket_scan.run_scan",
        "schedule": crontab(minute=0, hour=5, day_of_week="1-5"),
    },
    "postclose-scan": {
        "task": "app.tasks.premarket_scan.run_scan",
        "schedule": crontab(minute=0, hour=17, day_of_week="1-5"),
    },
    "watchlist-build": {
        "task": "app.tasks.watchlist_build.build_daily_watchlist",
        "schedule": crontab(minute=30, hour=17, day_of_week="1-5"),
    },

    # Position Monitoring — 3x daily (swing trading)
    "position-monitor-morning": {
        "task": "app.tasks.position_monitor.monitor_positions",
        "schedule": crontab(minute=0, hour=10, day_of_week="1-5"),
    },
    "position-monitor-midday": {
        "task": "app.tasks.position_monitor.monitor_positions",
        "schedule": crontab(minute=0, hour=13, day_of_week="1-5"),
    },
    "position-monitor-close": {
        "task": "app.tasks.position_monitor.monitor_positions",
        "schedule": crontab(minute=15, hour=16, day_of_week="1-5"),
    },

    # Regime Detection — once daily after close
    "regime-detection": {
        "task": "app.tasks.regime_detection.run_regime_detection",
        "schedule": crontab(minute=0, hour=17, day_of_week="1-5"),
    },

    # Daily Wrap-up
    "daily-meta-review": {
        "task": "app.tasks.daily_meta_review.run_daily_meta_review",
        "schedule": crontab(minute=45, hour=17, day_of_week="1-5"),
    },
    "daily-performance": {
        "task": "app.tasks.performance_calc.calc_daily_performance",
        "schedule": crontab(minute=0, hour=18, day_of_week="1-5"),
    },

    # Maintenance
    "weekly-universe-update": {
        "task": "app.tasks.universe_update.refresh_all_universes",
        "schedule": crontab(minute=0, hour=3, day_of_week="0"),
    },
}
