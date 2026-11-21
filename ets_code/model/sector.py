# sector.py
import numpy as np
import copy

from .helpers import (
    time_left,
    is_auction_round,
)


class c_sector(list):
    def __init__(self, p):
        super().__init__()
        for j in range(p.N):
            self.append(c_firm(p, j, self))

        self.D, self.E, self.Q, self.alloc_traded = np.zeros((4, p.T + 2))
        self.Sales = np.zeros(p.T + 2)
        self.Profit = np.zeros(p.T + 2)
 

        for j in self:
            j.s[0] = 1 / p.N

        self.D[0] = p.A - sum([j.s[0] * j.price[0] for j in self]) * p.b
        for j in self:
            j.D[0] = j.qg[0] = j.s[0] * self.D[0]
            j.sales[0] = min(j.D[0], j.qg[0])
            j.inv[0] = j.qg[0] - j.sales[0]
            
            # j.E[0] = j.qg[0] * j.e0[0]

    def aggregate_production(self, p, t):
        """原 c_sector.production，重命名以避免与 c_firm.production 混淆"""
        self.apply("production", p, t)
        self.E[t] = sum(j.E[t] for j in self)
        self.Q[t] = sum(j.qg[t] for j in self)

    def apply(self, method, p, t):
        for obj in self:
            getattr(obj, method)(p, t)


class c_firm:
    def __init__(self, p, j, sec):
        self.j = j
        self.sec = sec
        self.mac_slope = p.mac_slope[j]
        self.lr = p.lr[j]
        self.tech_threshold = p.tech_threshold[j]
 
        self.λ = copy.deepcopy(p.λ[j])
        self.λ0 = copy.deepcopy(p.λ[j])

        # ===== 修改：计算基准期平均利润/平均排放作为初始报价 =====
        # 初始化时先设置一个默认值，稍后在基准期结束后更新
        self.ini_reserved_price = 0.0  # 将在基准期后计算
        
        # 用于累计基准期数据
        self.caseline_profit_sum = 0.0
        self.caseline_emissions_sum = 0.0
        self.caseline_rounds = 0
 
        self.production_plan = 0.0
        self.uncovered = 0.0  # 本期未被配额覆盖的排放，期末结算
        self.last_abatement_time = 0
        self.min_abatement_interval = p.min_abatement_interval

        (
            self.s, self.sq, self.f, self.E, self.qg, self.D, self.U, self.price,
            self.m, self.e0, self.c, self.p_quote, self.allocs_need, self.alloc_inventory,
            self.alloc_traded, self.alloc_cash_flow, self.alloc_avg_cost
        ) = np.zeros((17, p.T + 2))
        
        self.inv = np.zeros(p.T + 2)
        self.sales = np.zeros(p.T + 2)
        self.revenue = np.zeros(p.T + 2)
        self.cost = np.zeros(p.T + 2)
        self.profit = np.zeros(p.T + 2)
        self.free_alloc_received = np.zeros(p.T + 2)

        self.m[0] = p.initial_markup[j]
        self.price[0] = p.c0[j] * (1 + p.initial_markup[j])
        self.e0[0] = self.e0[1] = p.e0[j]
        self.c[0] = self.c[1] = p.c0[j]
        
        # ===== 修改：初始报价暂时设为0，将在基准期后计算 =====
        if p.alloc_market:
            # 暂时设置为一个占位值
            self.p_quote[p.t_start] = 0.0  # 将在基准期结束后更新

    def calculate_initial_quote(self, p):
        """在基准期结束后计算初始报价 = 平均利润/平均排放"""
        avg_profit = self.caseline_profit_sum / self.caseline_rounds
        avg_emissions = self.caseline_emissions_sum / self.caseline_rounds
        self.ini_reserved_price = avg_profit / avg_emissions
        
        # 设置初始报价（不再使用discount factor）
        self.p_quote[p.t_start] = self.ini_reserved_price
        
        # 向前传播初始报价到t_start之前的所有时期
        for t in range(p.t_start):
            self.p_quote[t] = self.ini_reserved_price

    def accumulate_baseline_data(self, t):
        """在基准期内累计利润和排放数据"""
        self.caseline_profit_sum += self.profit[t]
        self.caseline_emissions_sum += self.E[t]
        self.caseline_rounds += 1
 
    def set_expectations(self, p, t):
        # 在 sector.py 中使用
        self.production_plan = (self.D[t - 1] + 
                            p.production_trend_weight * (self.D[t - 1] - self.D[t - 2])) if t > 1 else self.D[0]
        exp_inv_rate = 0 
        self.production_plan = max(0.0, self.production_plan*(1 + exp_inv_rate) - self.inv[t - 1])

        if t != 1 and self.s[t - 2] > 0:
            self.m[t] = self.m[t - 1] * (1 + p.markup_adjust_rate * (self.s[t - 1] - self.s[t - 2]) / self.s[t - 2])
        else:
            self.m[t] = self.m[t - 1]

    def auction_buy(self, p, t):
        """
        一级市场（拍卖）购买配额 - 采用基于MAC的真实价值投标策略
        """
        # 1. 计算拍卖中的配额需求 (逻辑与之前类似)
        horizon = time_left(p, t)
        base_need = self.production_plan * self.e0[t] * horizon
        
        self.allocs_need[t] = base_need   - self.alloc_inventory[t]
        
        p.ex.orders.append([self.p_quote[t], self.allocs_need[t], self])


 
    def secondary_trade(self, p, t):
        """
        二级市场交易 - 可以买入和卖出配额
        """
        horizon = time_left(p, t)
        
        base_need = self.production_plan * self.e0[t] * horizon
        self.allocs_need[t] = base_need  - self.alloc_inventory[t]
        
        # 二级市场可以买卖
        if self.allocs_need[t] != 0:
            p.ex.orders.append([self.p_quote[t], self.allocs_need[t], self])

    def production(self, p, t):
        self.qg[t] = self.production_plan
        self.E[t] = self.qg[t] * self.e0[t]

        if p.gov.alloc_market:
            if p.use_penalty:
                avail = self.alloc_inventory[t]
                used = min(avail, self.E[t])
                self.uncovered += self.E[t] - used
                self.alloc_inventory[t] = max(0.0, avail - used)
                self.alloc_inventory[t + 1] = self.alloc_inventory[t]
            else:
                if self.e0[t] * p.time_left_fn(p, t) > 0:
                    self.qg[t] = min(self.production_plan, self.alloc_inventory[t] / (self.e0[t] * p.time_left_fn(p, t)))
                else:
                    p.report_error("Error in production(): self.e0[t]*time_left<=0")
                self.E[t] = self.qg[t] * self.e0[t]
                self.alloc_inventory[t] = self.alloc_inventory[t + 1] = self.alloc_inventory[t] - self.E[t]

        self.price[t] = max(0, (self.e0[t] * p.gov.market_px[t] + self.c[t]) * (1 + self.m[t]))
        
 
    def abatement(self, p, t):
        # 初始化下期参数为当期值
        self.e0[t + 1] = self.e0[t]
        self.c[t + 1] = self.c[t]
        
        # 早期退出条件
        if (t < p.t_start or 
            t - self.last_abatement_time < self.min_abatement_interval or
            len(self.λ) == 0):
            return
        
        # 获取最优减排技术
        a, b = self.λ[0]
        MAC = b / a if a != 0 else np.inf
        
        # 计算决策价格
        decision_price = self._get_decision_price(p, t)
        
        # 减排决策
        if p.abatement and MAC * (1 + self.tech_threshold) <= decision_price:
            self.λ.pop(0)
            self.last_abatement_time = t
            self.e0[t + 1] = self.e0[t] - a
            self.c[t + 1] = self.c[t] + b

    def _get_decision_price(self, p, t):
        """最近 r_min 轮（含当轮）市场价格的均值"""
        r_min = max(1, min(t, self.min_abatement_interval))
        return float(np.mean([p.gov.market_px[t - l] for l in range(r_min)]))

def trade_commodities(p, t):
    """
    商品市场结算：只传 p；函数内部用 sec = p.sec
    """
    sec = p.sec

    # 1) 竞争力
    for j in sec:
        j.f[t] = - (p.w[0] * j.price[t] + p.w[1] * j.e0[t] + p.w[2] * j.U[t - 1])

    # 2) 份额更新
    f_mean = sum([j.f[t] * j.s[t - 1] for j in sec])
    if f_mean != 0:
        for j in sec:
            j.s[t] = max(0, j.s[t - 1] * (1 - p.market_selection_rate * (j.f[t] - f_mean) / f_mean))
        total_share = sum([j.s[t] for j in sec])
        if total_share > 0:
            for j in sec:
                j.s[t] /= total_share
    else:
        for j in sec:
            j.s[t] = j.s[t - 1]

    # 3) 总需求
    p_mean = sum([j.s[t] * j.price[t] for j in sec])
    sec.D[t] = max(0.0, p.A - p.b * p_mean)

    # 4) 分配、销量、库存、财务
    for j in sec:
        j.D[t] = j.s[t] * sec.D[t]
        available = j.inv[t - 1] + j.qg[t]
        j.sales[t] = min(j.D[t], available)
        j.inv[t] = available - j.sales[t]
        j.U[t] = j.D[t] - j.sales[t]
        j.revenue[t] = j.price[t] * j.sales[t]
        production_cost = j.c[t] * j.qg[t]
        j.cost[t] = production_cost + j.alloc_cash_flow[t]
        j.profit[t] = j.revenue[t] - j.cost[t]
        
        # ===== 新增：在基准期内累计数据 =====
        if t <= p.baseline_period * p.t_period:
            j.accumulate_baseline_data(t)
        
        # ===== 新增：在基准期结束后计算初始报价 =====
        if t == p.baseline_period * p.t_period:
            j.calculate_initial_quote(p)

    # 5) 汇总
    sec.Sales[t] = sum(j.sales[t] for j in sec)
    sec.Profit[t] = sum(j.profit[t] for j in sec)
