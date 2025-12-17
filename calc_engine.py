import numpy as np
import pandas as pd

# India-specific climate zones (ECBC-based)
INDIA_CLIMATE_ZONES = {
    "Hot-Dry": {
        "examples": "Rajasthan, Gujarat, Maharashtra interior",
        "cooling_months": 8,
        "heating_months": 2,
        "ground_temp_C": 28,
        "suitability_score": 3
    },
    "Warm-Humid": {
        "examples": "Kerala, Goa, Chennai, Coastal Karnataka",
        "cooling_months": 10,
        "heating_months": 0,
        "ground_temp_C": 26,
        "suitability_score": 3
    },
    "Composite": {
        "examples": "Delhi, Punjab, Haryana, UP",
        "cooling_months": 6,
        "heating_months": 3,
        "ground_temp_C": 24,
        "suitability_score": 3
    },
    "Temperate": {
        "examples": "Himachal Pradesh, Uttarakhand",
        "cooling_months": 3,
        "heating_months": 6,
        "ground_temp_C": 18,
        "suitability_score": 2
    },
    "Cold": {
        "examples": "Jammu & Kashmir, Ladakh, High altitude",
        "cooling_months": 1,
        "heating_months": 8,
        "ground_temp_C": 12,
        "suitability_score": 2
    }
}

# Indian building cooling intensity by tier (kW/m2)
INDIA_COOLING_INTENSITY = {
    "Office": {"Tier-1": 0.18, "Tier-2": 0.14, "Tier-3": 0.10},
    "Educational": {"Tier-1": 0.13, "Tier-2": 0.10, "Tier-3": 0.07},
    "Residential": {"Tier-1": 0.12, "Tier-2": 0.08, "Tier-3": 0.05},
    "Hospital": {"Tier-1": 0.22, "Tier-2": 0.18, "Tier-3": 0.15},
    "Hotel": {"Tier-1": 0.18, "Tier-2": 0.14, "Tier-3": 0.10},
    "IT/Tech Park": {"Tier-1": 0.20, "Tier-2": 0.16, "Tier-3": 0.12}
}

# State-wise electricity rates (Rs/kWh) - 2024-25 approximate
INDIA_ELECTRICITY_RATES = {
    "Maharashtra": {"commercial": 9.5, "residential": 7.2},
    "Delhi": {"commercial": 8.0, "residential": 6.5},
    "Tamil Nadu": {"commercial": 7.5, "residential": 5.0},
    "Karnataka": {"commercial": 8.5, "residential": 6.8},
    "Gujarat": {"commercial": 7.0, "residential": 5.5},
    "Rajasthan": {"commercial": 8.2, "residential": 6.0},
    "Uttar Pradesh": {"commercial": 7.8, "residential": 6.2},
    "West Bengal": {"commercial": 8.0, "residential": 6.5},
    "Telangana": {"commercial": 8.3, "residential": 6.0},
    "Kerala": {"commercial": 7.2, "residential": 5.8},
    "Punjab": {"commercial": 7.5, "residential": 6.0},
    "Haryana": {"commercial": 7.8, "residential": 6.3},
    "National Average": {"commercial": 8.5, "residential": 6.5}
}

# Soil thermal conductivity (W/m·K)
INDIA_SOIL_TYPES = {
    "Alluvial Plains": 2.2,
    "Black Soil": 1.8,
    "Red Soil": 1.6,
    "Laterite": 1.4,
    "Sandy": 2.5,
    "Rocky/Hard": 3.0
}

# Capital cost estimates (Rs/kW of cooling capacity)
CAPITAL_COST_PER_KW = {
    "Hot-Dry": 120000,
    "Warm-Humid": 160000,
    "Composite": 140000,
    "Temperate": 150000,
    "Cold": 180000
}

class ValidationError(Exception):
    pass

class CalculationEngine:
    def __init__(self, defaults=None):
        self.defaults = defaults or {}
        self.weights = {
            'load': 0.25,
            'capacity': 0.25,
            'energy': 0.3,
            'climate': 0.2
        }

    def validate_inputs(self, inputs):
        if 'buildingArea_m2' not in inputs or inputs['buildingArea_m2'] <= 0:
            raise ValidationError('Invalid building area (buildingArea_m2)')
        if 'peakCooling_kW' in inputs and inputs['peakCooling_kW'] and inputs['peakCooling_kW'] <= 0:
            raise ValidationError('peakCooling_kW must be > 0')
        if 'gsHeatPumpCOP' in inputs and inputs['gsHeatPumpCOP'] <= 0:
            raise ValidationError('gsHeatPumpCOP must be > 0')

    def estimate_peak_cooling(self, inputs):
        """Estimate peak cooling based on Indian building standards"""
        btype = inputs.get('buildingType', 'Office')
        tier = inputs.get('buildingTier', 'Tier-2')
        area = inputs.get('buildingArea_m2', 0)
        
        # Get intensity based on building type and tier
        if btype in INDIA_COOLING_INTENSITY:
            if isinstance(INDIA_COOLING_INTENSITY[btype], dict):
                intensity = INDIA_COOLING_INTENSITY[btype].get(tier, 0.15)
            else:
                intensity = INDIA_COOLING_INTENSITY[btype]
        else:
            intensity = 0.15
        
        return area * intensity

    def simple_thermal_model(self, inputs):
        """Calculate loads and capacity"""
        load_kW = inputs.get('peakCooling_kW') or self.estimate_peak_cooling(inputs)
        oversize = inputs.get('oversize_factor', 1.2)
        capacity_kW = load_kW * oversize
        c_l_ratio = capacity_kW / max(load_kW, 1e-6)
        return {
            'load_kW': round(load_kW, 3), 
            'capacity_kW': round(capacity_kW, 3), 
            'c_l_ratio': round(c_l_ratio, 3)
        }

    def ground_loop_sizing(self, inputs, peak_load_kW):
        """Calculate ground loop requirements using soil conductivity"""
        soil_k = inputs.get('soilConductivity_WpmK', 2.0)
        climate = inputs.get('climate', 'Composite')
        climate_data = INDIA_CLIMATE_ZONES.get(climate, INDIA_CLIMATE_ZONES['Composite'])
        
        # Simplified heat transfer calculation
        # Typical ground loop: 15-20 W/m depending on soil
        watts_per_meter = soil_k * 8  # Empirical factor
        required_loop_length_m = (peak_load_kW * 1000) / watts_per_meter
        
        # Assume 100m deep boreholes
        borehole_count = max(1, round(required_loop_length_m / 100, 0))
        
        # Land area assuming 5m x 5m spacing
        land_area_m2 = borehole_count * 25
        
        return {
            'loop_length_m': round(required_loop_length_m, 0),
            'borehole_count': int(borehole_count),
            'land_area_m2': round(land_area_m2, 0),
            'watts_per_meter': round(watts_per_meter, 1)
        }

    def energy_estimate(self, inputs, model_out):
        """Calculate annual energy consumption"""
        climate = inputs.get('climate', 'Composite')
        climate_data = INDIA_CLIMATE_ZONES.get(climate, INDIA_CLIMATE_ZONES['Composite'])
        
        # Calculate operating hours based on climate
        cooling_hours = climate_data['cooling_months'] * 180  # ~6 hrs/day avg
        heating_hours = climate_data['heating_months'] * 120  # ~4 hrs/day avg
        total_hours = cooling_hours + heating_hours
        
        cop = inputs.get('gsHeatPumpCOP', 4.0)
        annual_kWh = model_out['load_kW'] * total_hours / max(cop, 0.1)
        
        baseline_cop = inputs.get('baseline_COP', 3.0)
        baseline_kWh = model_out['load_kW'] * total_hours / max(baseline_cop, 0.1)
        
        savings_kWh = baseline_kWh - annual_kWh
        
        return {
            'annual_kWh': round(annual_kWh, 2),
            'baseline_kWh': round(baseline_kWh, 2),
            'savings_kWh': round(savings_kWh, 2),
            'operating_hours': total_hours
        }

    def economic_analysis(self, inputs, energy_out, model_out):
        """Calculate costs and payback in Indian Rupees"""
        state = inputs.get('state', 'National Average')
        btype = inputs.get('buildingType', 'Office')
        climate = inputs.get('climate', 'Composite')
        
        # Get electricity rate
        rate_category = "commercial" if btype in ["Office", "Hospital", "Hotel", "IT/Tech Park"] else "residential"
        rates = INDIA_ELECTRICITY_RATES.get(state, INDIA_ELECTRICITY_RATES["National Average"])
        electricity_rate = rates[rate_category]
        
        # Annual costs
        geotabs_cost_INR = energy_out['annual_kWh'] * electricity_rate
        baseline_cost_INR = energy_out['baseline_kWh'] * electricity_rate
        annual_savings_INR = energy_out['savings_kWh'] * electricity_rate
        
        # Capital cost estimate
        cost_per_kw = CAPITAL_COST_PER_KW.get(climate, 140000)
        capital_cost_INR = model_out['capacity_kW'] * cost_per_kw
        
        # Simple payback
        if annual_savings_INR > 0:
            payback_years = capital_cost_INR / annual_savings_INR
        else:
            payback_years = 999
        
        return {
            'electricity_rate': electricity_rate,
            'geotabs_cost_INR': round(geotabs_cost_INR, 2),
            'baseline_cost_INR': round(baseline_cost_INR, 2),
            'annual_savings_INR': round(annual_savings_INR, 2),
            'capital_cost_INR': round(capital_cost_INR, 2),
            'payback_years': round(payback_years, 1)
        }

    def co2_estimate(self, energy_kwh, emission_factor=0.82):
        """Calculate CO2 emissions in tonnes"""
        return round(energy_kwh * emission_factor / 1000.0, 3)

    def ranking_scores(self, inputs, model_out, energy_out, economics):
        """Calculate feasibility scores"""
        scores = {}
        
        # Load score based on area
        a = inputs.get('buildingArea_m2', 0)
        scores['load'] = min(3, max(0, int(a / 500)))
        
        # Capacity adequacy
        cl = model_out['c_l_ratio']
        scores['capacity'] = 3 if cl >= 1.1 else (2 if cl >= 0.9 else 1)
        
        # Energy savings score
        sk = energy_out['savings_kWh']
        if sk <= 0:
            scores['energy'] = 0
        elif sk < 10000:
            scores['energy'] = 1
        elif sk < 30000:
            scores['energy'] = 2
        else:
            scores['energy'] = 3
        
        # Climate suitability
        climate = inputs.get('climate', 'Temperate')
        climate_data = INDIA_CLIMATE_ZONES.get(climate, INDIA_CLIMATE_ZONES['Composite'])
        scores['climate'] = climate_data['suitability_score']
        
        # Economic score (new)
        payback = economics['payback_years']
        if payback < 5:
            scores['economic'] = 3
        elif payback < 8:
            scores['economic'] = 2
        elif payback < 12:
            scores['economic'] = 1
        else:
            scores['economic'] = 0
        
        return scores

    def run(self, inputs):
        """Main calculation pipeline"""
        merged = {**self.defaults, **(inputs or {})}
        
        # Auto-estimate peak cooling if missing
        peak = merged.get("peakCooling_kW")
        if peak in [None, "", 0]:
            merged["peakCooling_kW"] = round(self.estimate_peak_cooling(merged), 2)
            merged["peakCooling_source"] = "Estimated from Indian building standards"
        else:
            merged["peakCooling_kW"] = float(peak)
            merged["peakCooling_source"] = "User defined"
        
        # Validate
        self.validate_inputs(merged)
        
        # Run calculations
        model_out = self.simple_thermal_model(merged)
        ground_loop = self.ground_loop_sizing(merged, model_out['capacity_kW'])
        energy_out = self.energy_estimate(merged, model_out)
        economics = self.economic_analysis(merged, energy_out, model_out)
        
        # CO2 calculations
        co2_geotabs = self.co2_estimate(energy_out['annual_kWh'])
        co2_baseline = self.co2_estimate(energy_out['baseline_kWh'])
        co2_savings = self.co2_estimate(energy_out['savings_kWh'])
        
        # Scoring
        scores = self.ranking_scores(merged, model_out, energy_out, economics)
        total_score = sum(scores.values())
        
        # Feasibility recommendation (now out of 15 with economic score)
        if total_score >= 12:
            feasibility = "Highly Feasible"
        elif total_score >= 8:
            feasibility = "Conditionally Feasible"
        else:
            feasibility = "Not Recommended"
        
        weighted = sum(self.weights.get(k, 0) * scores.get(k, 0) for k in self.weights)
        
        # Get climate data for output
        climate = merged.get('climate', 'Composite')
        climate_data = INDIA_CLIMATE_ZONES.get(climate, INDIA_CLIMATE_ZONES['Composite'])
        
        return {
            "inputs": merged,
            "model": model_out,
            "ground_loop": ground_loop,
            "energy": energy_out,
            "economics": economics,
            "co2": {
                "geotabs_tonnes": co2_geotabs,
                "baseline_tonnes": co2_baseline,
                "savings_tonnes": co2_savings
            },
            "co2_savings_tonnes": co2_savings,
            "climate_data": climate_data,
            "scores": scores,
            "total_score": total_score,
            "weighted_score": round(weighted, 3),
            "feasibility_recommendation": feasibility
        }