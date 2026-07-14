"""
KPI Calculator Tool
"""

class KPICalculator:
    def calculate(self, metric_type: str, params: dict) -> dict:
        calculators = {
            "turnover_rate": self._calc_turnover,
            "engagement_score": self._calc_engagement,
        }
        
        calc_fn = calculators.get(metric_type)
        if not calc_fn:
            return {"error": f"Metric '{metric_type}' không được hỗ trợ."}
            
        result = calc_fn(**params)
        result["disclaimer"] = "⚠️ Đây là kết quả mô phỏng. Vui lòng xác thực với dữ liệu thực tế."
        return result

    def _calc_turnover(self, current_rate=0.15, target_rate=0.10, headcount=1000, avg_replacement_cost=50000):
        savings = headcount * (float(current_rate) - float(target_rate)) * float(avg_replacement_cost)
        return {
            "current_rate": f"{float(current_rate)*100:.1f}%",
            "target_rate": f"{float(target_rate)*100:.1f}%",
            "potential_savings": f"${savings:,.0f}",
            "analysis": f"Tiết kiệm ước tính ~${savings:,.0f}/năm."
        }
        
    def _calc_engagement(self, **kwargs):
        return {"analysis": "Mô phỏng điểm engagement tăng 1.5 điểm sau chương trình."}
