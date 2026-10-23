// Included after the original binding helpers in the generated translation unit.
void configure_weather(BoundWorld&w,py::dict p){
    keys(p,{"enabled","year_s","transition_s","change_s","temperature_bias_c"});
    if(!py::isinstance<py::bool_>(p["enabled"]))throw py::value_error("INVALID_CLIMATE_BOOL");
    uw::ClimateConfig c{py::cast<bool>(p["enabled"]),number(p["year_s"]),number(p["transition_s"]),number(p["change_s"]),number(p["temperature_bias_c"])};
    w.core.configure_climate(c);
}
py::dict condition(const uw::Conditions&c){return py::dict("offset_c"_a=c.offset,"cloud_fraction"_a=c.cloud,"rain_mm_h"_a=c.rain,"wind_m_s"_a=py::make_tuple(c.wind_x,c.wind_y));}
py::dict weather_snapshot(const BoundWorld&w){
    const auto&s=w.core.season();const auto&c=w.core.climate();const auto&v=w.core.weather();
    py::dict exposure;py::list shelters;
    for(const auto&e:w.core.entities())if(e.kind=="lean_to"||(e.kind=="construction"&&e.recipe_id=="lean_to"))
        shelters.append(py::dict("entity_id"_a=e.id,"position_m"_a=py::make_tuple(e.position.x,e.position.y),"coverage_radius_m"_a=1.1,"capacity"_a=4,"condition"_a=e.health,"work_s"_a=e.work_s,"complete"_a=(e.kind=="lean_to"),"composition_ug"_a=e.composition,"mass_ug"_a=std::to_string(e.mass_ug),"entrance"_a="open perimeter; no solid walls","roof_height_m"_a=2.0));
    for(const auto&[id,e]:w.core.exposures())exposure[py::str(id)]=py::dict("wetness"_a=e.wetness,"cold_burden"_a=e.cold,"environmental_fatigue_added"_a=e.fatigue_added,"environmental_health_lost"_a=e.health_lost,"shelter_id"_a=e.shelter);
    return py::dict("version"_a=1,"enabled"_a=c.enabled,"tick"_a=std::to_string(w.core.tick()),"source"_a="native_authored_climate_v1","exposure"_a=exposure,"shelters"_a=shelters,
        "year_s"_a=c.year_s,"day_s"_a=86400,"season"_a=s.name,"year_index"_a=std::to_string(s.year),"phase_progress"_a=s.progress,
        "weather"_a=w.core.weather_kind(),"ambient_c"_a=w.core.ambient_c(),"daylight_factor"_a=s.daylight,"growth_factor"_a=s.growth,
        "current"_a=condition(w.core.conditions()),"from"_a=condition(v.from),"target"_a=condition(v.target),
        "forced"_a=(v.forced_until_s>w.core.tick()*w.core.dt()),"forced_until_s"_a=v.forced_until_s,"forcing_history"_a=v.forcing_requests,
        "transition_start_s"_a=v.start_s,"transition_end_s"_a=v.end_s,"next_change_s"_a=v.next_s,"rng"_a=std::to_string(v.rng));
}
py::dict weather_observation(const BoundWorld&w,const std::string&id){
    const auto&map=w.core.exposures();
    if(!w.core.climate().enabled||!map.contains(id))return py::dict("enabled"_a=false);
    const auto&e=map.at(id);const auto&c=w.core.conditions();
    py::list shelters;
    for(const auto&s:w.core.nearby(id))if(s.kind=="lean_to"||(s.kind=="construction"&&s.recipe_id=="lean_to"))
        shelters.append(py::dict("entity_id"_a=s.id,"position_m"_a=py::make_tuple(s.position.x,s.position.y),"complete"_a=(s.kind=="lean_to"),"condition"_a=s.health,"work_s"_a=s.work_s,"coverage_radius_m"_a=1.1,"capacity"_a=4));
    return py::dict("enabled"_a=true,"tick"_a=std::to_string(w.core.tick()),"source"_a="own_native_senses",
        "felt_temperature_c"_a=std::round(w.core.ambient_c()),"rain"_a=(c.rain>.05?(c.rain>6?"heavy":"light"):"none"),
        "clouds"_a=(c.cloud>.65?"overcast":c.cloud>.35?"cloudy":"clear"),"wind"_a=(std::hypot(c.wind_x,c.wind_y)>3?"windy":"calm"),
        "wetness"_a=e.wetness,"cold_burden"_a=e.cold,"shelter_id"_a=e.shelter,"observed_shelters"_a=shelters);
}
