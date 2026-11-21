# helpers.py
import numpy as np


def aggregate_by_period(series_t, p, how="sum"):
    vals, idx = [], []
    for k in range(1, p.TP + 1):
        t0 = (k - 1) * p.t_period + 1
        t1 = k * p.t_period
        seg = series_t[t0:t1 + 1]
        if how == "mean":
            vals.append(np.nanmean(seg))
        else:
            vals.append(np.nansum(seg))
        idx.append(k)
    return np.array(idx), np.array(vals)

 


# helpers.py 里加一个小函数
def round_number_in_period(p, t):
    """
    返回 t 在本监管期内是第几场拍卖（1-based）。
    若 t 不是拍卖回合，返回 0。
    """
    pos = time_position(p, t)           # 0..t_period-1
    slots = auction_round_positions(p)  # 例如 [0, 4, 8]（auctions_per_period=3）
    if pos not in slots:
        return 0
    return slots.index(pos) + 1         # 1..len(slots)
 
def time_left(p, t):
    return p.t_period - (t - 1) % p.t_period


def time_position(p, t):
    return (t - 1) % p.t_period

def auction_round_positions(p):
    """
    返回本监管期中进行拍卖的 '回合索引(从0开始)' 列表。
    例如 t_period=12, auctions_per_period=4 -> [0,3,6,9]
                 =3 -> [0,4,8]
                 =1 -> [0]
    """
    n = max(1, int(getattr(p, "auctions_per_period", 1)))
    pos = [int(np.floor(i * p.t_period / n)) for i in range(n)]
    pos = sorted(set(max(0, min(p.t_period - 1, x)) for x in pos))
    return pos

def is_auction_round(p, t):
    """回合 t 是否为拍卖轮。"""
    return time_position(p, t) in auction_round_positions(p)


def get_auction_share(p, t):
    """
    返回回合 t 的拍卖占比 ∈ [0,1]，按固定步长逐期提高：
      - t < p.t_start: 0（政策未启动）
      - 第 1 个监管期（k=1）: 0（免费分配）
      - 从第 2 个监管期起: auction_share = p.auction_step * (k - 1)
      - 超过实施期后锁定为末值
    """
    if t < p.t_start:
        return 0.0  # 政策未启动前不拍

    k = reg_year_index(p, t)  # 启动后的第 k 个监管期（1..）
    k = min(k, p.t_trans) if getattr(p, "t_trans", None) else k  # 只在实施期内爬坡

    steps = max(0, k - 1)  # 第一个监管期免费分配
    val = p.auction_step * steps

    return float(np.clip(val, 0.0, 1.0))


 

def impl_window_end_round(p):
    return p.t_start + p.t_trans * p.t_period - 1


def in_banking_window(p, t):
    if not getattr(p, "allow_banking", False):
        return False
    if getattr(p, "bank_until_impl_end", True):
        return p.t_start <= t <= impl_window_end_round(p)
    return True


def baseline_E_per_round(p, n_periods):
    t1 = p.t_start - 1
    t0 = max(1, p.t_start - n_periods * p.t_period)
    return float(np.mean([p.sec.E[t] for t in range(t0, t1 + 1)]))


def reg_year_index(p, t):
    if t < p.t_start:
        return 0
    return ((t - p.t_start) // p.t_period) + 1


def period_index(p, t):
    return (t - 1) // p.t_period + 1

def get_future_auction_times_in_period(p, t):
    """获取本期未来的拍卖时间点（不包括当前）"""
    period_start = t - time_position(p, t)
    pos = time_position(p, t)
    slots = auction_round_positions(p)
    if pos not in slots:
        return []
    current_idx = slots.index(pos)
    future_slots = slots[current_idx + 1:]
    return [period_start + s for s in future_slots]


# =========================
# Metrics
# =========================
 
def compute_metrics_series(p, damage_coeff):
    """
    回合序列版指标：每回合的利润、CS、政府收入、损害、社会福利（已贴现）。
    只传 p；内部用 p.sec。
    """
    sec = p.sec
    T = p.T
    profit_t = np.zeros(T + 1)
    cs_t = np.zeros(T + 1)
    govR_t = np.zeros(T + 1)
    penalty_t = np.zeros(T + 1)
    damage_t = np.zeros(T + 1)
    sw_t = np.zeros(T + 1)

    use_penalty = getattr(p, "use_penalty", False)
    has_P = hasattr(p.gov, "P")

    b = float(p.b)  # 已有
   

    for t in range(1, T + 1):
        # 政府
        if p.alloc_market:
            govR_t[t] = p.gov.R[t]
            if use_penalty and has_P:
                penalty_t[t] = p.gov.P[t]

        # 损害
        damage_t[t] = damage_coeff * sec.E[t]

        # 利润
        prf = 0.0
        Q_t = 0.0
        for j in sec:
            revenue = j.price[t] * j.sales[t]
            production_cost = j.c[t] * j.qg[t]
            alloc_cash = j.alloc_cash_flow[t] if p.alloc_market else 0.0
            prf += (revenue - (production_cost + alloc_cash))
            Q_t += j.sales[t]                  # >>> 新增：行业销量
        profit_t[t] = prf


        Q_sold_t = 0.0
        p_mean_t = 0.0
        share_sum = 0.0
        for j in sec:
            Q_sold_t += j.sales[t]
            p_mean_t += j.s[t] * j.price[t]
            share_sum += j.s[t]
        # alpha = float(p.A) / b if b > 0 else 0.0
        # cs_raw = Q_sold_t * (alpha - p_mean_t) - (Q_sold_t**2) / (2.0 * b)

        cs_t[t] = (Q_sold_t**2) / (2.0 * b)


        # 社会福利（把 CS 计入）
        if use_penalty and has_P:
            sw_t[t] = profit_t[t] + cs_t[t] + govR_t[t] + penalty_t[t] - damage_t[t]
        else:
            sw_t[t] = profit_t[t] + cs_t[t] + govR_t[t] - damage_t[t]

    out = {
        "profit_t": profit_t,
        "cs_t": cs_t,
        "govR_t": govR_t,
        "damage_t": damage_t,
        "sw_t": sw_t,
        "penalty_t": penalty_t,
    }
    if use_penalty:
        out["penalty_t"] = penalty_t
        out["gov_total_t"] = govR_t + penalty_t
    return out
