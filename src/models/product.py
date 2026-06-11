from datetime import datetime

from pydantic import BaseModel, Field


class Product(BaseModel):
    """产品数据模型"""
    id: int = Field(..., description="产品ID")
    name: str = Field(..., description="产品名称")
    description: str = Field(..., description="产品描述")
    price: float = Field(..., gt=0, description="产品价格")
    stock: int = Field(..., ge=0, description="库存数量")
    category: str = Field(..., description="产品分类")
    specifications: dict[str, str] = Field(default_factory=dict, description="产品规格参数")
    created_at: datetime | None = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime | None = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "智能手机Pro Max",
                "description": "6.7英寸超视网膜XDR显示屏",
                "price": 8999.00,
                "stock": 150,
                "category": "电子产品",
                "specifications": {
                    "屏幕": "6.7英寸OLED",
                    "处理器": "A17仿生"
                }
            }
        }

class ProductCreate(BaseModel):
    """创建产品请求模型"""
    name: str = Field(..., min_length=1, max_length=200, description="产品名称")
    description: str = Field(..., min_length=1, description="产品描述")
    price: float = Field(..., gt=0, description="产品价格")
    stock: int = Field(..., ge=0, description="库存数量")
    category: str = Field(..., min_length=1, description="产品分类")
    specifications: dict[str, str] = Field(default_factory=dict, description="产品规格参数")

class ProductUpdate(BaseModel):
    """更新产品请求模型"""
    name: str | None = Field(None, min_length=1, max_length=200, description="产品名称")
    description: str | None = Field(None, min_length=1, description="产品描述")
    price: float | None = Field(None, gt=0, description="产品价格")
    stock: int | None = Field(None, ge=0, description="库存数量")
    category: str | None = Field(None, min_length=1, description="产品分类")
    specifications: dict[str, str] | None = Field(None, description="产品规格参数")

class ProductSearch(BaseModel):
    """产品搜索请求模型"""
    keyword: str = Field(..., min_length=1, description="搜索关键词")
    category: str | None = Field(None, description="产品分类过滤")
    min_price: float | None = Field(None, ge=0, description="最低价格")
    max_price: float | None = Field(None, ge=0, description="最高价格")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制")
