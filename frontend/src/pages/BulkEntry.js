import { useState, useEffect } from "react";
import axios from "axios";
import { Camera, XCircle, Check } from "@phosphor-icons/react";
import { GMD_CATEGORIES, GMD_EQUIPMENT } from "@/lib/gmdConfig";
import { getApiBase } from "@/lib/api";

const API = getApiBase();

// Centralized, reusable parameter schema mapping configuration
const CATEGORY_PARAMETERS = {
  "Blowers": [
    "vertical_vibration",
    "horizontal_vibration",
    "axial_vibration",
    "temperature"
  ],
  "DM Water Electrode Cooling": [
    "tds",
    "water_temperature",
    "pump_pressure"
  ],
  "Cooling Tower Water Monitoring": [
    "hardness",
    "ph",
    "tds"
  ]
};

// Map machine key patterns to readable titles dynamically
const formatParameterLabel = (key) => {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

// Map parameters to their specific engineering display units
const getUnit = (key) => {
  if (key.includes("vibration")) return "mm/s";
  if (key.includes("temperature") || key.includes("temp")) return "°C";
  if (key === "ph") return "";
  if (key === "tds" || key === "hardness") return "ppm";
  if (key.includes("pressure")) return "bar";
  return "";
};

const BulkEntry = () => {
  // Core structured GMD application tracking states
  const [selectedCategory, setSelectedCategory] = useState("");
  const [equipmentList, setEquipmentList] = useState([]);
  const [selectedEquipment, setSelectedEquipment] = useState("");
  
  // Cleaned dynamic execution states
  const [readings, setReadings] = useState({});
  const [remarks, setRemarks] = useState("");
  const [technician, setTechnician] = useState("");

  // Communication, processing, and error handling states
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoBase64, setPhotoBase64] = useState(null);
  const [photoFilename, setPhotoFilename] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(null);

  // Sync Equipment dropdown array listing when Category selection updates
  useEffect(() => {
    if (selectedCategory) {
      setEquipmentList(GMD_EQUIPMENT[selectedCategory] || []);
    } else {
      setEquipmentList([]);
    }
    setSelectedEquipment("");
    setReadings({});
    setSubmitError(null);
    setSubmitSuccess(null);
  }, [selectedCategory]);

  // FIX #1: Only regenerate parameter fields when category changes (Removed selectedEquipment dependency)
  useEffect(() => {
    if (!selectedCategory) {
      setReadings({});
      return;
    }

    const defaultFields = CATEGORY_PARAMETERS[selectedCategory] || [];
    const initialReadings = {};
    
    defaultFields.forEach((field) => {
      initialReadings[field] = "";
    });
    
    setReadings(initialReadings);
  }, [selectedCategory]);

  const handlePhotoCapture = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPhotoFilename(file.name || "");
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoBase64(reader.result);
        setPhotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleValueChange = (field, value) => {
    setReadings((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const formatApiError = (error) => {
    const detail = error.response?.data?.detail;
    if (!detail) return error.message;
    if (typeof detail === "string") return detail;
    return detail.message || "Submission failed";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCategory || !selectedEquipment || submitting) return;

    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      // Build clean normalized dataset filtering out empty/null parameters completely
      const normalizedReadings = {};
      Object.keys(readings).forEach((key) => {
        if (readings[key] !== "" && readings[key] !== null) {
          normalizedReadings[key] = Number(readings[key]);
        }
      });

      // Exact payload serialization matching the FastAPI contract
      const payload = {
        category: selectedCategory,
        equipment: selectedEquipment,
        readings: normalizedReadings,
        verified_by: technician.trim(),
        remarks: remarks.trim(),
        entry_source: "Web"
      };
      console.log("API Base:", API);
      console.log("Final URL:", `${API}/gmd/condition-monitoring/bulk`);
      console.log("Payload:", payload);
      await axios.post(`${API}/gmd/condition-monitoring/bulk`, payload);

      setSubmitSuccess(`Saved readings successfully for ${selectedEquipment}.`);

      // FIX #2: Maintain visual form visibility. Reset values, maintain asset targets.
      const resetReadings = {};
      (CATEGORY_PARAMETERS[selectedCategory] || []).forEach((field) => {
        resetReadings[field] = "";
      });
      setReadings(resetReadings);
      setRemarks("");
      setPhotoPreview(null);
      setPhotoBase64(null);
      setPhotoFilename("");
    } catch (error) {
      console.error("GMD bulk submit error:", error);
      setSubmitError(formatApiError(error));
    } finally {
      setSubmitting(false);
    }
  };

  const paramKeys = Object.keys(readings);

  return (
    <div className="w-full max-w-[1920px] mx-auto p-4 md:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-4xl font-light tracking-tight text-zinc-950">Bulk Reading Entry</h1>
        <p className="text-sm font-medium text-zinc-800 mt-1">Neutral Glass</p>
        <p className="text-sm text-zinc-600 mt-0.5">GMD Condition Monitoring System</p>
        <p className="text-sm text-zinc-700 mt-2">
          Enter operational diagnostics parameters for your selected GMD field hardware.
        </p>
      </div>

      <div className="border border-zinc-200 bg-white p-6 mb-6">
        <h3 className="text-lg font-medium tracking-tight text-zinc-900 mb-4">Select Area</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block">
              Category *
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
            >
              <option value="">Select Category</option>
              {GMD_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block">
              Equipment *
            </label>
            <select
              value={selectedEquipment}
              onChange={(e) => setSelectedEquipment(e.target.value)}
              className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
              disabled={!selectedCategory}
            >
              <option value="">Select Equipment</option>
              {equipmentList.map((eq) => (
                <option key={eq} value={eq}>
                  {eq}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {submitError && (
        <div className="border-2 border-[#E11D48] bg-red-50 text-red-800 px-4 py-3 mb-6 text-sm">
          {submitError}
        </div>
      )}
      {submitSuccess && (
        <div className="border-2 border-[#16A34A] bg-green-50 text-green-800 px-4 py-3 mb-6 text-sm">
          {submitSuccess}
        </div>
      )}

      {selectedCategory && selectedEquipment && paramKeys.length > 0 && (
        <form onSubmit={handleSubmit}>
          <div className="border border-zinc-200 bg-white p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-medium tracking-tight text-zinc-900">
                  {selectedEquipment} — Parameter Specifications
                </h3>
                <p className="text-sm text-zinc-600 mt-1">
                  Category Type: {selectedCategory}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-zinc-50">
                  <tr className="border-b-2 border-zinc-200">
                    <th className="text-left px-4 py-3 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 sticky left-0 bg-zinc-50">
                      Parameter Name
                    </th>
                    <th className="text-center px-4 py-3 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500">
                      Value Input
                    </th>
                    <th className="text-center px-4 py-3 text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-400">
                      Unit
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paramKeys.map((param, idx) => (
                    <tr
                      key={param}
                      className={`border-b border-zinc-100 ${
                        idx % 2 === 0 ? "bg-white" : "bg-zinc-50/50"
                      }`}
                    >
                      <td className="px-4 py-4 text-sm font-medium text-zinc-950 sticky left-0 bg-inherit">
                        {formatParameterLabel(param)} *
                      </td>
                      <td className="px-4 py-2 flex justify-center">
                        <input
                          type="number"
                          step="0.01"
                          value={readings[param] || ""}
                          onChange={(e) => handleValueChange(param, e.target.value)}
                          className="w-32 border border-zinc-200 px-3 py-1.5 text-sm font-mono text-center rounded-none focus:ring-1 focus:ring-[#002FA7]"
                          placeholder="0.00"
                          required
                        />
                      </td>
                      <td className="px-4 py-2 text-center text-xs font-mono text-zinc-500">
                        {getUnit(param) || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-3 block">
                  Verification photo (if any alarm/warning)
                </label>
                {!photoPreview ? (
                  <label className="flex items-center space-x-2 px-4 py-3 border-2 border-dashed border-zinc-300 hover:border-[#002FA7] bg-white cursor-pointer transition-all duration-150 rounded-none">
                    <Camera size={20} weight="bold" className="text-[#002FA7]" />
                    <span className="text-sm text-zinc-700">Capture / Upload Photo</span>
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={handlePhotoCapture}
                      className="hidden"
                    />
                  </label>
                ) : (
                  <div className="relative inline-block">
                    <img
                      src={photoPreview}
                      alt="Preview"
                      className="w-48 h-36 object-cover border-2 border-[#002FA7]"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setPhotoPreview(null);
                        setPhotoBase64(null);
                        setPhotoFilename("");
                      }}
                      className="absolute top-2 right-2 bg-[#E11D48] text-white p-1 hover:bg-[#E11D48]/90"
                    >
                      <XCircle size={16} weight="fill" />
                    </button>
                  </div>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block">
                    Engineer&apos;s name *
                  </label>
                  <input
                    type="text"
                    value={technician}
                    onChange={(e) => setTechnician(e.target.value)}
                    placeholder="Enter your name"
                    className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[10px] sm:text-xs uppercase tracking-[0.2em] font-bold text-zinc-500 mb-2 block">
                    Remarks
                  </label>
                  <input
                    type="text"
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="Enter any observational notes"
                    className="w-full border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-950 focus:outline-none focus:ring-2 focus:ring-[#002FA7] focus:ring-offset-2 rounded-none"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => {
                setSelectedEquipment("");
                // Reconstruct a blank object for the parameters rather than wiping keys completely
                const blankReadings = {};
                (CATEGORY_PARAMETERS[selectedCategory] || []).forEach((f) => {
                  blankReadings[f] = "";
                });
                setReadings(blankReadings);
              }}
              className="border border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400 px-6 py-3 text-sm font-medium tracking-tight transition-all duration-150 ease-out rounded-none"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-[#16A34A] text-white hover:bg-[#16A34A]/90 px-8 py-3 text-sm font-medium tracking-tight transition-all duration-150 ease-out rounded-none disabled:opacity-50 flex items-center space-x-2"
            >
              {submitting ? (
                <span>Submitting...</span>
              ) : (
                <>
                  <Check size={18} weight="bold" />
                  <span>Submit All Metrics</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {!selectedEquipment && selectedCategory && (
        <div className="border border-zinc-200 bg-white p-12 text-center">
          <p className="text-zinc-500">Please choose a target operational hardware component to log readings</p>
        </div>
      )}

      {!selectedCategory && (
        <div className="border border-zinc-200 bg-white p-12 text-center">
          <p className="text-zinc-500">Select a structural system category to start bulk entry</p>
        </div>
      )}
    </div>
  );
};

export default BulkEntry; 