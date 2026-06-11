
class KnowledgeBase:
    """
    知识库服务 - 管理常见问题和答案

    功能：
    - 存储常见问题和答案
    - 语义相似度匹配
    - 动态知识更新
    """

    def __init__(self):
        self.knowledge_items = self._load_default_knowledge()

    def _load_default_knowledge(self) -> list[dict]:
        """加载默认知识库"""
        return [
            {
                "question": "配送时间",
                "answer": "一般3-5个工作日，偏远地区可能需要5-7天。特殊商品（如大件家具）可能需要更长时间。",
                "keywords": ["配送", "发货", "快递", "物流", "时间", "几天"]
            },
            {
                "question": "退换货政策",
                "answer": "支持7天无理由退换货，商品需保持完好，不影响二次销售。定制商品、生鲜食品等特殊商品不支持退换。",
                "keywords": ["退换货", "退货", "换货", "退款", "7天"]
            },
            {
                "question": "客服工作时间",
                "answer": "客服工作时间：周一至周日 9:00-21:00，节假日正常服务。紧急问题可24小时留言。",
                "keywords": ["客服", "工作时间", "上班时间", "联系"]
            },
            {
                "question": "支付方式",
                "answer": "支持支付宝、微信支付、银行卡支付、花呗分期等多种支付方式。",
                "keywords": ["支付", "付款", "支付宝", "微信", "银行卡"]
            },
            {
                "question": "发票政策",
                "answer": "支持电子发票和纸质发票。电子发票订单完成后自动发送至邮箱，纸质发票随商品一同寄送。",
                "keywords": ["发票", "税票", "报销"]
            },
            {
                "question": "商品保修",
                "answer": "电子产品质保一年，其他商品质保三个月。保修期内非人为损坏可免费维修或更换。",
                "keywords": ["保修", "质保", "维修", "售后"]
            },
            {
                "question": "配送范围",
                "answer": "全国大部分地区支持配送，偏远地区、港澳台地区暂不支持配送。",
                "keywords": ["配送范围", "配送地区", "哪里"]
            },
            {
                "question": "订单取消",
                "answer": "未发货订单可申请取消，已发货订单需要先拒收再申请退款。定制商品不支持取消。",
                "keywords": ["取消订单", "撤销订单", "不要了"]
            },
            {
                "question": "价格保护",
                "answer": "商品下单后7天内，如遇降价可申请差价补偿。特殊促销商品不参与价格保护。",
                "keywords": ["价格保护", "降价", "差价"]
            },
            {
                "question": "会员权益",
                "answer": "会员享受积分奖励、专属折扣、生日礼遇等权益。积分可抵扣现金，100积分=1元。",
                "keywords": ["会员", "积分", "权益", "等级"]
            }
        ]

    async def query(self, question: str, top_k: int = 3) -> list[str]:
        """
        查询知识库

        Args:
            question: 用户问题
            top_k: 返回结果数量

        Returns:
            匹配的答案列表
        """
        scored_results = []

        for item in self.knowledge_items:
            score = self._calculate_similarity(question, item)
            if score > 0:
                scored_results.append((score, item["answer"]))

        # 按相似度排序
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # 返回top_k个结果
        return [result[1] for result in scored_results[:top_k]]

    def _calculate_similarity(self, question: str, knowledge_item: dict) -> float:
        """
        计算问题与知识库条目的相似度

        Args:
            question: 用户问题
            knowledge_item: 知识库条目

        Returns:
            相似度分数
        """
        score = 0
        question_lower = question.lower()

        # 关键词匹配
        for keyword in knowledge_item["keywords"]:
            if keyword in question_lower:
                score += 1

        # 问题标题匹配
        if knowledge_item["question"] in question:
            score += 2

        return score

    def add_knowledge(self, question: str, answer: str, keywords: list[str]):
        """
        添加新的知识条目

        Args:
            question: 问题
            answer: 答案
            keywords: 关键词列表
        """
        self.knowledge_items.append({
            "question": question,
            "answer": answer,
            "keywords": keywords
        })

    def get_all_knowledge(self) -> list[dict]:
        """获取所有知识条目"""
        return self.knowledge_items

    def update_knowledge(self, index: int, question: str = None, answer: str = None, keywords: list[str] = None):
        """
        更新知识条目

        Args:
            index: 条目索引
            question: 新问题（可选）
            answer: 新答案（可选）
            keywords: 新关键词（可选）
        """
        if 0 <= index < len(self.knowledge_items):
            if question:
                self.knowledge_items[index]["question"] = question
            if answer:
                self.knowledge_items[index]["answer"] = answer
            if keywords:
                self.knowledge_items[index]["keywords"] = keywords

    def delete_knowledge(self, index: int) -> bool:
        """
        删除知识条目

        Args:
            index: 条目索引

        Returns:
            删除是否成功
        """
        if 0 <= index < len(self.knowledge_items):
            del self.knowledge_items[index]
            return True
        return False
