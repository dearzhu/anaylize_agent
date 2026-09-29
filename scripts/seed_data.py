"""生成二期演示所需的样例数据（确定性，可重复运行）。

输出：
  data/sample_transactions/transactions.csv   交易流水
  data/sample_prices/prices.csv               行情（用于动量回测）

运行：python scripts/seed_data.py
"""
from __future__ import annotations

import csv
import datetime
import os

_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_dir(p: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)


def _lcg(n: int, seed: int = 7):
    """确定性伪随机序列，范围 [0,1)。"""
    x = seed
    out = []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (2 ** 31)
        out.append(x / (2 ** 31))
    return out


def seed_transactions(path: str | None = None) -> str:
    path = path or os.path.join(_ROOT, "data", "sample_transactions", "transactions.csv")
    _ensure_dir(path)
    # date, account, counterparty, type, amount, category
    rows = [
        ("2024-01-03", "ACC-001", "CUST-X", "in", 185000, "销售收入"),
        ("2024-01-05", "ACC-001", "SUP-A", "out", 92000, "采购付款"),
        ("2024-01-08", "ACC-001", "CUST-Y", "in", 64000, "销售收入"),
        ("2024-01-12", "ACC-001", "BANK-FEE", "out", 1200, "手续费"),
        ("2024-01-15", "ACC-001", "TAX-BUREAU", "out", 53000, "税款"),
        ("2024-01-18", "ACC-002", "SALARY-POOL", "out", 210000, "工资发放"),
        ("2024-01-22", "ACC-001", "CUST-X", "in", 73000, "销售收入"),
        ("2024-01-26", "ACC-001", "SUP-B", "out", 41000, "采购付款"),
        ("2024-02-02", "ACC-001", "CUST-Y", "in", 58000, "销售收入"),
        ("2024-02-06", "ACC-001", "SUP-A", "out", 88000, "采购付款"),
        ("2024-02-09", "ACC-003", "TAX-BUREAU", "out", 37000, "税款"),
        ("2024-02-13", "ACC-001", "CUST-X", "in", 96000, "销售收入"),
        ("2024-02-15", "ACC-001", "INVEST-CO", "in", 820000, "投资回款"),   # 异常大额
        ("2024-02-19", "ACC-001", "SUP-B", "out", 47000, "采购付款"),
        ("2024-02-23", "ACC-002", "SALARY-POOL", "out", 210000, "工资发放"),
        ("2024-02-27", "ACC-001", "CUST-Y", "in", 61000, "销售收入"),
        ("2024-03-01", "ACC-001", "SUP-A", "out", 95000, "采购付款"),
        ("2024-03-05", "ACC-001", "CUST-X", "in", 88000, "销售收入"),
        ("2024-03-08", "ACC-001", "BANK-FEE", "out", 1350, "手续费"),
        ("2024-03-10", "ACC-001", "SUP-A", "out", 760000, "大额预付"),       # 异常大额
        ("2024-03-14", "ACC-001", "CUST-Y", "in", 67000, "销售收入"),
        ("2024-03-18", "ACC-001", "SUP-B", "out", 44000, "采购付款"),
        ("2024-03-21", "ACC-003", "TAX-BUREAU", "out", 39000, "税款"),
        ("2024-03-25", "ACC-001", "CUST-X", "in", 91000, "销售收入"),
        ("2024-03-28", "ACC-002", "SALARY-POOL", "out", 210000, "工资发放"),
        ("2024-03-30", "ACC-001", "INVEST-CO", "transfer", 120000, "内部调拨"),
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "account", "counterparty", "type", "amount", "category"])
        w.writerows(rows)
    return path


def seed_prices(path: str | None = None) -> str:
    path = path or os.path.join(_ROOT, "data", "sample_prices", "prices.csv")
    _ensure_dir(path)
    n = 120
    rnd = _lcg(n, seed=7)
    price = 100.0
    start = datetime.date(2024, 1, 1)
    rows = []
    for i in range(n):
        drift = 0.0009
        vol = 0.02
        r = (rnd[i] - 0.5) * 2  # [-1,1]
        ret = drift + vol * r
        price *= (1 + ret)
        d = start + datetime.timedelta(days=i)
        rows.append((d.isoformat(), round(price, 2)))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        w.writerows(rows)
    return path


def ensure_sample_data() -> None:
    seed_transactions()
    seed_prices()


if __name__ == "__main__":
    ensure_sample_data()
    print("sample data generated: transactions.csv + prices.csv")
