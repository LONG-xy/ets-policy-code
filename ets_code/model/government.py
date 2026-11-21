# government.py
import numpy as np

from .helpers import (
    baseline_E_per_round,
    reg_year_index,
    time_position,
    in_banking_window,
    get_auction_share,
    get_future_auction_times_in_period,  # 若需要引用，请保留
)

class c_government:
    def __init__(self, p):
        self.qp, self.market_px, self.R = np.zeros((3, p.T + 2))
        self.alloc_market = False   # 是否开启当期许可市场
        self.x = 0                   # 政策实施进度
        self.P = np.zeros(p.T + 2)   # 罚款收入
        
        self.free_allocated = np.zeros(p.T + 2)        # 记录每期是否已完成免费分配
        self.auction_remainder = np.zeros(p.T + 2)     # 记录每轮未售出的配额
        self.free_alloc_per_period = np.zeros(p.T + 2)
        
        # —— 拍卖轮统计 —— #
        self.is_auction_round = np.zeros(p.T + 2, dtype=int)
        self.base_auction_qty = np.zeros(p.T + 2)      # 本轮“基准”拍卖量（不含滚入）
        self.rollover_in_qty = np.zeros(p.T + 2)       # 从前序轮滚入的量
        self.offered_qty = np.zeros(p.T + 2)           # 实际提供量（基准+滚入）
        self.unsold_qty = np.zeros(p.T + 2)            # 未售出量
        self.rollover_out_qty = np.zeros(p.T + 2)      # 本轮未售后滚到后续轮的量
        self.canceled_qty = np.zeros(p.T + 2)          # 若为期内最后一次拍卖而未售出的，记为作废量

    def update_policy(self, p, t):
        """每回合更新政策状态；如开启许可市场、设定配额、期初免费分配等。"""
        if t >= p.t_start:
            self.x = min((t - p.t_start) / p.t_period + 1, p.t_trans)
            if p.alloc_market:
                self.alloc_market = True
                self.set_allocs(p, t)
                # 每期第一回合，进行免费分配
                if time_position(p, t) == 0:
                    self.allocate_free_allocs_at_period_start(p, t)
 
    def allocate_free_allocs_at_period_start(self, p, t):
        """在每期开始时一次性完成所有免费分配"""
        sec = p.sec
        period_start = t - time_position(p, t)
        if self.free_allocated[period_start]:
            return
        
        E_base = baseline_E_per_round(p, n_periods=p.baseline_period)
        k_eff = min(reg_year_index(p, t), p.t_trans)
        frac = k_eff * p.E_step
        total_cap = max(0.0, E_base * (1.0 - frac)) * p.t_period
        
        share_now = get_auction_share(p, t)
        free_total = (1 - share_now) * total_cap
        
        if free_total > 0:
            # 按上一期产量占比分配（产出基准法）
            prev_t0 = period_start - p.t_period
            prev_t1 = period_start - 1
            Q_sum = sum(sec.Q[ti] for ti in range(prev_t0, prev_t1 + 1))
            for j in sec:
                hist_q = sum(j.qg[ti] for ti in range(prev_t0, prev_t1 + 1))
                # 极端政策下上一期总产量可能为 0，此时平均分配
                alloc_amount = free_total * (hist_q / Q_sum) if Q_sum > 0 else free_total / p.N
                j.alloc_inventory[t] += alloc_amount
                j.free_alloc_received[period_start] = alloc_amount

        self.free_allocated[period_start] = True
        self.free_alloc_per_period[period_start] = free_total

    def set_allocs(self, p, t):
        """设定本期（监管期）总许可量，并在期初处理结转或清零。"""
        sec = p.sec
        E_base = baseline_E_per_round(p, n_periods=p.baseline_period)
        k_eff = min(reg_year_index(p, t), p.t_trans)
        frac = k_eff * p.E_step
        cap_per_round = max(0.0, E_base * (1.0 - frac))
        self.qp[t] = cap_per_round * p.t_period

        # 仅在每期第一回合切换头寸（银行结转或清零）
        if time_position(p, t) == 0:
            for j in sec:
                j.alloc_inventory[t] = j.alloc_inventory[t - 1] if in_banking_window(p, t) else 0.0

    def settle_compliance_period(self, p, t):
        """在履约期末结算罚款"""
        sec = p.sec
        if not p.use_penalty or t < p.t_start:
            return
        
        period_start = t - p.t_period + 1
        period_end = t
        
        for j in sec:
            # 期末：剩余配额先覆盖本期未被覆盖的排放，差额按 ψ 罚款，余量结转
            # 期末先用剩余配额覆盖累计未覆盖排放，再结算罚款和结转余量。
            remaining = j.alloc_inventory[period_end]
            shortage = max(0.0, j.uncovered - remaining)
            banked = max(0.0, remaining - j.uncovered)
            j.alloc_inventory[period_end] = j.alloc_inventory[period_end + 1] = banked
            j.uncovered = 0.0

            if shortage > 0:
                penalty_cash = shortage * p.penalty_rate
                j.alloc_cash_flow[period_end] += penalty_cash
                self.P[period_end] += penalty_cash
