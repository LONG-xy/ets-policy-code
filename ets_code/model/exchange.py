# exchange.py
import numpy as np
from operator import itemgetter

from .helpers import period_index, round_number_in_period,auction_round_positions


class c_exchange:
    def __init__(self, p):
        self.orders = []
        # 3 行、p.T+2 列
        self.final_price_per_round, self.alloc_traded, self.t_r = np.zeros((3, p.T + 2))
        # self.t_r 每轮的交易次数计数器
        
        # 拍卖和免费分配的数量记录
        self.actual_auctioned = np.zeros(p.T + 2)

        # 记录每笔交易的价格和数量
        self.trade_prices = {}
        self.trade_volumes = {}

        # 撮合循环实际达到的最大迭代次数（用于核实 1000 次上限从未触及）
        self.max_match_iter = 0
        
 
    def auction_clear(self, p, t, ini_total_auction_qty=None):
        """
        拍卖：仅负责卖出 ini_total_auction_qty 的配额，不做免费分配
        返回: 未售出的配额数量
        """
        if ini_total_auction_qty is None:
            ini_total_auction_qty = 0.0
            
        ini_total_auction_qty = max(0.0, float(ini_total_auction_qty))

        # ========== 第1步：准备和排序订单 ==========
        
        # 随机打乱订单，避免同价格订单的固定优先级
        np.random.shuffle(self.orders)
        
         # 确保所有bid价格不低于政府设定的底价（floor price）
        for k in range(len(self.orders)):
            price, qty, firm = self.orders[k]
            
            # 只处理bid
            if qty >= 0:
                self.orders[k] = [max(price, p.floor_price), qty, firm]

        # 按价格升序排序所有订单， 排序规则就是按照元组的第一个元素（索引 0）来排序， 第0个元素是价格
        self.orders.sort(key=itemgetter(0))
        
        #  提取bid并反转为降序（从最高价开始）
        bids = [x for x in self.orders if x[1] >= 0][::-1]

        # ========== 第2步：执行统一价格拍卖 ==========
        
        Q = ini_total_auction_qty  # 剩余待分配数量
        success_bids = []  # 成功的竞标记录
        self.final_price_per_round[t] = 0.0 # 初始化本轮价格

        per = period_index(p, t)
        rn  = round_number_in_period(p, t)
        rn_total = len(auction_round_positions(p))  # 本期总拍卖场次= p.auctions_per_period (若设了)

        # print(f'在轮次 t={t}（监管期 {per} / 第 {rn}/{rn_total} 场拍卖的拍卖总量 {ini_total_auction_qty}）')
        # 统一价拍卖
        # 从最高价开始满足bid，直到配额售完
        # 安全上限：正常情况下每轮至少消化一个 bid 或清空 Q，最多 len(bids) 轮；
        # 设一个远高于此的上限以防极端参数下的浮点病态导致的死循环。
        _auction_iter = 0
        _auction_iter_max = 1000
        while len(bids) > 0 and Q > 0:
            _auction_iter += 1
            if _auction_iter > _auction_iter_max:
                p.report_error("Error in auction_clear: exceeded max matching iterations")
                break

            # 本次交易数量 = min(剩余配额, 当前bid需求)

            # if Q < bids[0][1]:
            #     print(f"[WARNING] 在轮次 t={t}（监管期 {per} / 第 {rn}/{rn_total} 场拍卖），"
            #         f"剩余拍卖量 {Q:.6f} < 最高bid需求 {bids[0][1]:.6f}，仅成交 {Q:.6f}。")

            q_traded = min(Q, bids[0][1])
            if q_traded <= 1e-12:
                if Q <= 1e-12:
                    Q = 0.0
                    break
                bids.pop(0)
                continue

            # 记录成功的竞标：[价格, 数量, 企业]
            success_bids.append([bids[0][0], q_traded, bids[0][2]])

            # 更新清算价格（最后一个成功竞标的价格）
            self.final_price_per_round[t] = bids[0][0]

            # 更新剩余量
            Q -= q_traded
            bids[0][1] -= q_traded

            # 如果当前bid已完全满足，从列表中移除（用 <= 容忍浮点误差）
            if bids[0][1] <= 1e-12:

                bids.pop(0)

        self.max_match_iter = max(self.max_match_iter, _auction_iter)

        # ========== 第3步：处理拍卖结果 ==========
        #  实际拍卖出的总量
        allocated_via_auction = 0.0
        
         # 确定最终清算价格（不低于底价）
        if len(success_bids) > 0:
            clear_price = max(self.final_price_per_round[t], p.floor_price)
            
            self.final_price_per_round[t] = clear_price
            
             # 处理每个成功的竞标
            for price, qty, firm in success_bids:
                # 更新企业的配额库存
                firm.alloc_inventory[t] += qty
                
                # 更新政府收入
                p.gov.R[t] += qty * clear_price
                
                # 更新企业的交易记录
                firm.alloc_traded[t] += qty
                # 更新企业现金流（购买成本）
                # 一个是支付的金额，一个是交易成本
                firm.alloc_cash_flow[t] += qty * clear_price
                firm.alloc_cash_flow[t] += qty * clear_price * p.tc_rate_b

                # 实际拍卖出的总量
                allocated_via_auction += qty
        else:
            self.final_price_per_round[t] = 0.0

        # ========== 第4步：学习机制 - 调整报价策略 ==========
 
        from collections import defaultdict

        EPS = 1e-4

        # 按企业汇总实际成交量
        traded_by_firm = defaultdict(float)
        for _, q, f in success_bids:
            traded_by_firm[f] += float(q)

        # 按企业汇总剩余未成交量（含部分成交未吃完）
        residual_by_firm = defaultdict(float)
        for _, q, f in bids:
            if q > EPS:
                residual_by_firm[f] += float(q)

        success_firms  = set(traded_by_firm.keys())
        residual_firms = set(residual_by_firm.keys())

        # 互斥三类
        fully_filled = success_firms - residual_firms      # 完全成交
        partial      = success_firms & residual_firms      # 部分成交
        failed       = residual_firms - success_firms      # 完全失败

        # 规则：完全成交 -> 降价；部分/失败 -> 涨价（各企业仅调整一次）
        for f in fully_filled:
            f.p_quote[t] *= (1 - f.lr)
        for f in (partial | failed):
            f.p_quote[t] *= (1 + f.lr)
            
        

        min_qty = min((q for _, q, _ in success_bids), default=float("nan"))
        max_qty = max((q for _, q, _ in success_bids), default=float("nan"))
        # print(f"[WARNING] 在轮次 t={t}（监管期 {per} / 第 {rn}/{rn_total} 场拍卖），成功bid数: {len(success_bids)}, 最小bid数量: {min_qty}, 最大bid数量: {max_qty}, 部分成功bid数: {len(partial)}, 未成交bid数: {len(failed)}, 未成交总需求: {sum(residual_by_firm[f] for f in failed)}")

        # 剩余总拍卖量
        unsold = ini_total_auction_qty - allocated_via_auction
        # if unsold >  EPS:
            # print(f"[INFO] 在轮次 t={t}（监管期 {per} / 第 {rn}/{rn_total} 场拍卖），未售出配额 {unsold},占比: {unsold / ini_total_auction_qty:.2%}")
        #     # 清空订单簿
        self.orders = []
        # 记录本轮实际拍卖量
        self.actual_auctioned[t] = allocated_via_auction
        
        
        
        return unsold

    def secondary_clear(self, p, t):
 
        # 初始化本时间步的交易记录
        if t not in self.trade_prices:
            self.trade_prices[t] = []
            self.trade_volumes[t] = []

        np.random.shuffle(self.orders)
        self.orders.sort(key=itemgetter(0))
        # 卖单是按价格从低到高（最低卖价在前）
        asks = [x for x in self.orders if x[1] < 0]
        # 买单按价格从高到低（最高买价在前）
        bids = [x for x in self.orders if x[1] >= 0][::-1]  
        
        # 更新交易轮次计数
        self.t_r[t] += 1
        
        #  判断市场是否活跃（有买有卖）
        # 条件1: 市场自然停止（没有买单或卖单）
        self.active = not (len(bids) == 0 or len(asks) == 0)

        success_bids, success_asks = [], []

        last_trade_price = None

        # ========== 第2步：连续双边匹配 ==========
        EPS = 1e-4

        # —— 撮合条件加容差 —— #
        # 条件2: 价格无法撮合（最高买价 < 最低卖价）
        # 最高买价 ≥ 最低卖价
        # 安全上限：每次撮合至少移除一个买单或卖单，正常最多 len(bids)+len(asks) 轮；
        # 设远高于此的上限以防极端参数下的浮点病态导致的死循环。
        _cda_iter = 0
        _cda_iter_max = 1000
        while len(bids) > 0 and len(asks) > 0 and bids[0][0] + EPS >= asks[0][0]:
            _cda_iter += 1
            if _cda_iter > _cda_iter_max:
                p.report_error("Error in secondary_clear: exceeded max matching iterations")
                break
            b = bids[0]
            a = asks[0]

            # 三种情形
            if b[1] > -a[1] + EPS:           # 买量 > 卖量
                q = -a[1]                    # 正数
                b[1] -= q
                success_asks.append(asks[0])
                asks.pop(0)
            elif b[1] + EPS < -a[1]:         # 买量 < 卖量
                q = b[1]
                a[1] += q                    # 仍为负数
                success_bids.append(bids[0])
                bids.pop(0)
            else:                            # 视作相等（含浮点接近）
                q = min(b[1], -a[1])
                success_asks.append(asks[0])
                success_bids.append(bids[0])
                bids.pop(0); asks.pop(0)

            # ========== 第3步：记录交易并更新账户 ==========
            # 成交价格采用卖方报价（Ask价格）
            trade_price = a[0] 

            last_trade_price = trade_price
            self.trade_prices[t].append(trade_price)
            self.trade_volumes[t].append(q)

            b[2].alloc_inventory[t] += q
            a[2].alloc_inventory[t] -= q
            self.alloc_traded[t] += q
            b[2].alloc_traded[t] += q
            a[2].alloc_traded[t] -= q
            b[2].alloc_cash_flow[t] += q * trade_price
            a[2].alloc_cash_flow[t] -= q * trade_price
            b[2].alloc_cash_flow[t] += q * trade_price * p.tc_rate_b
            a[2].alloc_cash_flow[t] -= q * trade_price * p.tc_rate_s

        self.max_match_iter = max(self.max_match_iter, _cda_iter)

        # # 决定当回合价格
        # if self.alloc_traded[t] == 0:
        #     self.final_price_per_round[t] = 0.0
        # else:
        #     if last_trade_price is not None:
        #         self.final_price_per_round[t] = last_trade_price
        # 决定当回合价格
        if self.alloc_traded[t] == 0:
            # 无成交：置 0，end_of_alloc_trade 中沿用最近一次观察到的市场价格
            self.final_price_per_round[t] = 0.0
        else:
            # 有成交时使用最后一笔交易价格
            if last_trade_price is not None:
                self.final_price_per_round[t] = last_trade_price

        for b in success_bids:
            b[2].p_quote[t] *= (1 - b[2].lr)
        for a in success_asks:
            a[2].p_quote[t] *= (1 + a[2].lr)
        for b in bids:
            b[2].p_quote[t] *= (1 + b[2].lr)
        for a in asks:
            a[2].p_quote[t] *= (1 - a[2].lr)

        self.orders = []

 

    def end_of_alloc_trade(self, p, t):
 
 
        if t > 1 and self.final_price_per_round[t] == 0:
            p.gov.market_px[t] = p.gov.market_px[t - 1]
        else:
            p.gov.market_px[t] = self.final_price_per_round[t]

        for j in p.sec:
            span = p.time_position_fn(p, t)
            paid_qty_window = [j.alloc_traded[ti]     for ti in range(t - span, t + 1)]
            paid_val_window = [j.alloc_cash_flow[ti]  for ti in range(t - span, t + 1)]
            paid_qty = sum(paid_qty_window)
            paid_val = sum(paid_val_window)
            if paid_qty > 0:
                j.alloc_avg_cost[t] = paid_val / paid_qty
            j.p_quote[t] = j.p_quote[t + 1] = max(0, j.p_quote[t])
