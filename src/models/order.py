from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING_PAYMENT = "待付款"
    PENDING_SHIPMENT = "待发货"
    SHIPPED = "已发货"
    DELIVERED = "已送达"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    REFUNDING = "退款中"
    REFUNDED = "已退款"

class OrderItem(BaseModel):
    """订单商品项模型"""
    product_id: int = Field(..., description="商品ID")
    product_name: str = Field(..., description="商品名称")
    quantity: int = Field(..., gt=0, description="购买数量")
    price: float = Field(..., gt=0, description="商品单价")
    
    @property
    def total_price(self) -> float:
        """计算商品总价"""
        return self.quantity * self.price

class Order(BaseModel):
    """订单数据模型"""
    order_id: str = Field(..., description="订单号")
    user_id: str = Field(..., description="用户ID")
    status: OrderStatus = Field(default=OrderStatus.PENDING_PAYMENT, description="订单状态")
    items: List[OrderItem] = Field(..., min_items=1, description="订单商品列表")
    total_amount: float = Field(..., gt=0, description="订单总金额")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="更新时间")
    
    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        """验证订单总金额是否正确"""
        if 'items' in values:
            calculated_total = sum(item.total_price for item in values['items'])
            if abs(v - calculated_total) > 0.01:  # 允许0.01的误差
                raise ValueError(f'订单总金额不正确，应为 {calculated_total}')
        return v
    
    def can_cancel(self) -> bool:
        """检查订单是否可以取消"""
        return self.status in [OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING_SHIPMENT]
    
    def can_refund(self) -> bool:
        """检查订单是否可以退款"""
        return self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.COMPLETED]
    
    def get_status_description(self) -> str:
        """获取订单状态描述"""
        descriptions = {
            OrderStatus.PENDING_PAYMENT: "订单已创建，等待付款",
            OrderStatus.PENDING_SHIPMENT: "付款成功，等待商家发货",
            OrderStatus.SHIPPED: "商家已发货，等待用户签收",
            OrderStatus.DELIVERED: "订单已送达",
            OrderStatus.COMPLETED: "订单已完成",
            OrderStatus.CANCELLED: "订单已取消",
            OrderStatus.REFUNDING: "退款处理中",
            OrderStatus.REFUNDED: "退款已完成"
        }
        return descriptions.get(self.status, "未知状态")

class OrderCreate(BaseModel):
    """创建订单请求模型"""
    user_id: str = Field(..., description="用户ID")
    items: List[Dict] = Field(..., min_items=1, description="订单商品列表")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    contact_phone: Optional[str] = Field(None, description="联系电话")

class OrderUpdate(BaseModel):
    """更新订单请求模型"""
    status: Optional[OrderStatus] = Field(None, description="订单状态")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    contact_phone: Optional[str] = Field(None, description="联系电话")

class TrackingInfo(BaseModel):
    """物流信息模型"""
    tracking_number: str = Field(..., description="物流单号")
    status: str = Field(..., description="物流状态")
    location: str = Field(..., description="当前位置")
    estimated_delivery: Optional[str] = Field(None, description="预计送达时间")
    tracking_history: Optional[List[Dict]] = Field(default_factory=list, description="物流追踪历史")