# simulation_ets.py
import numpy as np

# === 引用已有工具函数 ===
from .helpers import (
    aggregate_by_period,
    time_left,       
    time_position,
    auction_round_positions,
    is_auction_round,
    get_auction_share,
    impl_window_end_round,
    in_banking_window,
    baseline_E_per_round,
    reg_year_index,
    period_index,
    get_future_auction_times_in_period,
    compute_metrics_series,
)

# === 导入模块 ===
from .government import c_government
from .exchange import c_exchange
from .sector import c_sector, trade_commodities

# =========================
# Parameters
# =========================
class c_parameters:
    def __init__(self, param_dict,   allow_banking=None, baseline_period=None, auctions_per_period=None):
 
        self.TP = param_dict.get('TP')
        self.t_period = param_dict.get('t_period')
        self.t_start = self.t_period * int(max(1, baseline_period or param_dict.get('baseline_period'))) + 1
        self.t_trans = param_dict.get('t_trans')
        self.A = param_dict.get('A')
        self.e0 = param_dict.get('e0')
        self.c0 = param_dict.get('c0')

        self.n_abatement_steps = param_dict.get('n_abatement_steps')
        self.floor_price = param_dict.get('floor_price')
        self.auction_step = param_dict.get('auction_step')
        self.allow_banking = allow_banking if allow_banking is not None else param_dict.get('allow_banking')
        self.bank_until_impl_end = param_dict.get('bank_until_impl_end')
        self.baseline_period = int(max(1, baseline_period or param_dict.get('baseline_period')))
        self.use_penalty = param_dict.get('use_penalty')
        self.penalty_rate = param_dict.get('penalty_rate')
        self.auctions_per_period = auctions_per_period if auctions_per_period is not None else param_dict.get('auctions_per_period')
        self.min_abatement_interval = param_dict.get('min_abatement_interval')
        self.discount_rate = param_dict.get('discount_rate')
        
        self.tc_rate_b = param_dict.get('tc_rate_b', 0.0)
        self.tc_rate_s = param_dict.get('tc_rate_s', 0.0)


        # 企业参数
        self.N = int(round(param_dict.get('N')))
        self.b = param_dict.get('b')
        self.E_step = param_dict.get('E_step')
        self.initial_markup = param_dict.get('initial_markup')
        self.markup_adjust_rate = param_dict.get('markup_adjust_rate')
        self.market_selection_rate = param_dict.get('market_selection_rate')
        self.lr = param_dict.get('lr')
        self.max_abatement_ratio = param_dict.get('max_abatement_ratio')
        self.mac_slope = param_dict.get('mac_slope')
        self.tech_threshold = param_dict.get('tech_threshold')

        # 企业异质性参数
        self.heterogeneity_b = param_dict.get('heterogeneity_b')

        # 其他参数
        self.b = self.b
        self.T = self.t_period * self.TP
 
        
        # 在企业参数部分添加
        self.production_trend_weight = param_dict.get('production_trend_weight')
 
        # 在 c_parameters.__init__ 中
        w_price = param_dict.get('w_price' )
        w_emission = param_dict.get('w_emission' )
        w_delivery = param_dict.get('w_delivery' )

        w_raw = np.array([w_price, w_emission, w_delivery], dtype=float)
        self.w = (w_raw / w_raw.sum()).tolist()
 
        self.abatement = True

        # 运行期对象占位
        self.sec = 0
        self.gov = 0
        self.ex = 0

        self.error = False
        self.log = []

        # 模式开关（由场景加载）
        self.alloc_market = False

        # —— 轻量函数指针，减少 import 依赖 —— #
        self.time_position_fn = time_position
        self.time_left_fn = time_left
 
    def generate_random_parameter(self):
        N = self.N
        rng = np.random

        # 基础扰动
        lr  = [self.lr  * (1 + self.heterogeneity_b  * (rng.random() - 0.5)) for _ in range(N)]
        e0  = np.random.normal(self.e0, 0.1, N)  
        B0  = [self.c0  * (1 + self.heterogeneity_b * (rng.random() - 0.5)) for _ in range(N)]
        mac_slope_list = [self.mac_slope * (1 + self.heterogeneity_b * (rng.random() - 0.5)) for _ in range(N)]

        tech_threshold = [self.tech_threshold * (1 + self.heterogeneity_b * (rng.random() - 0.5)) for _ in range(N)]
        
        initial_markup = [
            self.initial_markup * (1 + self.heterogeneity_b * (rng.random() - 0.5))
            for _ in range(N)
        ]

        # e0 → max_abatement_ratio_list（Sigmoid，超简）
        L, H = self.max_abatement_ratio  
        z = (e0 - e0.mean()) / e0.std()
        #  s = 1 / (1 + np.exp(-1.5 * z)) 
        s = 1 / (1 + np.exp(-z))   # 固定斜率 1.5 ，需要更敏感就调大
        max_abatement_ratio_list = (L + (H - L) * s).tolist()
        
        return [lr, e0.tolist(), B0, mac_slope_list, tech_threshold, max_abatement_ratio_list, initial_markup]
 
    def load_random_parameter(self, random_par):
        self.lr, self.e0, self.c0, self.mac_slope, self.tech_threshold, self.max_abatement_ratio_list, self.initial_markup = random_par
        self.λ = []
        for i in range(self.N):
            self.λ.append(self.generate_λ(self.mac_slope[i], self.e0[i], self.max_abatement_ratio_list[i]))

    def generate_λ(self, mac_slope, e0, max_abatement_ratio_j):
        λ = []
        # 等宽阶梯；b/a 即该层边际减排成本（MAC）
        for i in range(self.n_abatement_steps):
            a = (e0 * max_abatement_ratio_j) / self.n_abatement_steps
            MAC_i = a * mac_slope * (i + 1)
            b = a * MAC_i
            λ.append([a, b])
        return λ

    def report_error(self, statement):
        self.error = True
        if statement not in self.log:
            self.log.append(statement)

    # --- Scenarios ---
    def load_scenario(self, scenario):
        getattr(self, scenario)()

    def No_Policy(self):
        self.mode = "No Policy"
        self.alloc_market = False
        # 关掉投资减排技术
        self.abatement = False

    def ETS(self):
        self.mode = "ETS"
        self.alloc_market = True


# =========================
# Main dynamics
# =========================
def run_model(
    scenarios,
    param_dict,  # 改为param_dict
    damage_coeff=None,
    return_metrics=True,
    print_errors=False,
    random_par=None,
    allow_banking=None,
    baseline_period=None,
    auctions_per_period=None,
):
    results = []
    metrics = []
    
    # 处理damage_coeff参数
    if damage_coeff is None:
        damage_coeff = param_dict.get('damage_coeff', 1.0)

    if random_par is None:
        _tmp = c_parameters(
            param_dict,
            allow_banking=allow_banking,
            baseline_period=baseline_period,
            auctions_per_period=auctions_per_period,
        )
        random_par_local = _tmp.generate_random_parameter()
    else:
        random_par_local = random_par

    for scenario in scenarios:
        p = c_parameters(
            param_dict,
            allow_banking=allow_banking,
            baseline_period=baseline_period,
            auctions_per_period=auctions_per_period,
        )
        p.load_scenario(scenario)
        p.load_random_parameter(random_par_local)

        # 挂载运行期对象
        p.sec = c_sector(p)
        p.gov = c_government(p)
        p.ex = c_exchange(p)

        t = 1
        while t <= p.T:
            # 每期首回合更新政策
            if (t - 1) % p.t_period == 0:
                p.gov.update_policy(p, t)

            # 期望
            p.sec.apply("set_expectations", p, t)

            # 许可市场
            if p.gov.alloc_market:
            
                # 每期第一回合：免费分配 + 拍卖配额初始化
                if time_position(p, t) == 0:
                    p.gov.allocate_free_allocs_at_period_start(p, t)
                    period_start = t
                    Q_total_period = p.gov.qp[period_start]
                    share_now = get_auction_share(p, t)
                    p.gov.period_auction_total = share_now * Q_total_period
                    p.gov.period_auction_per_round = p.gov.period_auction_total / p.auctions_per_period

                p.ex.active = True
                while p.ex.active:
 
                    # === 修改后的代码：根据市场类型分别调用 ===
                    if p.mode == "ETS" and is_auction_round(p, t):
                        # 一级市场（拍卖）：企业只能下买单
                        p.sec.apply("auction_buy", p, t)
                        
                        p.gov.is_auction_round[t] = 1
                        base_auction = p.gov.period_auction_per_round
                        roll_in = p.gov.auction_remainder[t]
                        auction_qty = base_auction + roll_in

                        p.gov.base_auction_qty[t] = base_auction
                        p.gov.rollover_in_qty[t] = roll_in
                        p.gov.offered_qty[t] = auction_qty

                        unsold = p.ex.auction_clear(p, t, ini_total_auction_qty=auction_qty)

                        p.gov.unsold_qty[t] = unsold

                        if unsold > 0:
                            future_rounds = get_future_auction_times_in_period(p, t)
                            if len(future_rounds) > 0:
                                rollover_per_round = unsold / len(future_rounds)
                                for future_t in future_rounds:
                                    p.gov.auction_remainder[future_t] += rollover_per_round
                                p.gov.rollover_out_qty[t] = unsold
                                p.gov.canceled_qty[t] = 0.0
                            else:
                                p.gov.rollover_out_qty[t] = 0.0
                                p.gov.canceled_qty[t] = unsold

                        p.ex.active = False
                    else:
                        # 二级市场：企业可以买入和卖出
                        p.sec.apply("secondary_trade", p, t)
                        
                        # 二级市场撮合
                        p.ex.secondary_clear(p, t)
                    # 防死循环：每轮最多 1000 次撮合与重新报价
                    if p.ex.t_r[t] >= 1000:
                        p.report_error("Secondary market reached 1000 requoting iterations")
                        p.ex.active = False

                p.ex.end_of_alloc_trade(p, t)

            # —— 生产与商品市场 —— #
            p.sec.aggregate_production(p, t)
            trade_commodities( p, t)
            p.sec.apply("abatement", p, t)

            # —— 履约罚款（期末） —— #
            if p.gov.alloc_market and p.use_penalty and time_position(p, t) == p.t_period - 1:
                p.gov.settle_compliance_period(p, t)

            t += 1

        # 仅保存 p（sec/government/exchange 都挂在 p 上）
        results.append(p)

        if return_metrics:
            m_series = compute_metrics_series(p, damage_coeff=damage_coeff)
            metrics.append(m_series)

        if print_errors and p.error:
            print("Errors found in Scenario ", scenario)
            print(p.log)

    return results, metrics

# =========================
# Thin wrapper
# =========================
def simulate_ets(
    param_dict,  # 改为param_dict
    damage_coeff=None,
    fixed_random_par=None,
    allow_banking=None,
    baseline_period=None,
    auctions_per_period=None,
):
    """
    简化后的对外接口：只返回 (p_ets, metrics)
    - p_ets 包含 p_ets.sec / p_ets.gov / p_ets.ex 及全部时间序列
    """
    if damage_coeff is None:
        damage_coeff = param_dict.get('damage_coeff', 1.0)
        
    if fixed_random_par is None:
        _tmp = c_parameters(
            param_dict,
 
            allow_banking=allow_banking,
            baseline_period=baseline_period,
            auctions_per_period=auctions_per_period,
        )
        fixed_random_par = _tmp.generate_random_parameter()

    results, metrics = run_model(
        ["No_Policy", "ETS"],
        param_dict,
 
        damage_coeff=damage_coeff,
        return_metrics=True,
        print_errors=False,
        random_par=fixed_random_par,
        allow_banking=allow_banking,
        baseline_period=baseline_period,
        auctions_per_period=auctions_per_period,
    )

    # 取 ETS 场景的 p
    p_ets = results[1]
    return p_ets, metrics
