.PHONY: help install all test lint verify verify-playoffs app clean

help:
	@echo "install          安装依赖 (pip install -r requirements.txt)"
	@echo "all              按正确顺序跑完所有维度, 写出 results/"
	@echo "test             跑测试 (数据契约 + 引擎 + 指标构造)"
	@echo "lint             代码检查"
	@echo "verify           常规赛数据校验 (对照 Basketball-Reference)"
	@echo "verify-playoffs  季后赛数据校验 (对照 ESPN)"
	@echo "app              启动仪表盘"
	@echo "clean            清理缓存"

install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

all:
	python -m nbastars.run

test:
	pytest

lint:
	ruff check nbastars tests scripts notebooks app.py

# 需要先下载参考数据, 见 scripts/verify_reference_data.py 顶部说明
verify:
	python scripts/verify_reference_data.py --ref-dir $${REF_DIR:-/tmp/nba_verify}

verify-playoffs:
	python scripts/verify_playoffs_espn.py --cache $${ESPN_CACHE:-/tmp/nba_verify/hoopr}

app:
	streamlit run app.py

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +