# Author: Florian Mayer <florian.mayer@bitsrc.org>
#
# This module was developed with funding provided by
# the ESA Summer of Code (2011).

# The template can be found in tools/hektemplate.py
# Unless you are editing the template, DO NOT EDIT THIS FILE.
# ALL CHANGES WILL BE LOST THE NEXT TIME IT IS GENERATED FROM THE TEMPLATE.

"""
Attributes that can be used to construct HEK queries. They are different to
the VSO ones in that a lot of them are wrappers that conveniently expose
the comparisons by overloading Python operators. So, e.g., you are able
to say AR & AR.NumSpots < 5 to find all active regions with less than 5 spots.
As with the VSO query, you can use the fundamental logic operators AND and OR
to construct queries of almost arbitrary complexity. Note that complex queries
result in multiple requests to the server which might make them less efficient.
"""
from sunpy.net import attr
from sunpy.time import parse_time


# Ugly hack for the deprecated apply decorator, this needs to be cleaned up
def apply(f):
    return f()


class _ParamAttr(attr.Attr):
    """ A _ParamAttr is used to represent equality or inequality checks
    for certain parameters. It stores the attribute's name, the operator to
    compare with, and the value to compare to. """

    def __init__(self, name, op, value):
        attr.Attr.__init__(self)
        self.name = name
        self.op = op
        self.value = value

    def collides(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.op == other.op and self.name == other.name


# XXX: Why is this here but never used.
class _BoolParamAttr(_ParamAttr):
    def __init__(self, name, value='true'):
        _ParamAttr.__init__(self, name, '=', value)

    def __neg__(self):
        if self.value == 'true':
            return _BoolParamAttr(self.name, 'false')
        else:
            return _BoolParamAttr(self.name)

    def __pos__(self):
        return _BoolParamAttr(self.name)


class _ListAttr(attr.Attr):
    """ A _ListAttr is used when the server expects a list of things with
    the name (GET parameter name) key. By adding the _ListAttr to the query,
    item is added to that list. """

    def __init__(self, key, item):
        attr.Attr.__init__(self)

        self.key = key
        self.item = item

    def collides(self, other):
        return False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return vars(self) == vars(other)

    def __hash__(self):
        return hash(tuple(vars(self).items()))


class EventType(attr.Attr):
    def __init__(self, item):
        attr.Attr.__init__(self)
        self.item = item

    def collides(self, other):
        return isinstance(other, EventType)

    def __or__(self, other):
        if isinstance(other, EventType):
            return EventType(self.item + ',' + other.item)
        else:
            return super().__or__(other)


# XXX: XOR
class Time(attr.Attr):
    """ Restrict query to time range between start and end. """

    def __init__(self, start, end):
        attr.Attr.__init__(self)
        self.start = start
        self.end = end

    def collides(self, other):
        return isinstance(other, Time)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return vars(self) == vars(other)

    def __hash__(self):
        return hash(tuple(vars(self).items()))

    @classmethod
    def dt(cls, start, end):
        return cls(parse_time(start), parse_time(end))


class SpatialRegion(attr.Attr):
    def __init__(self, x1=-5000, y1=-5000, x2=5000, y2=5000,
                 sys='helioprojective'):
        attr.Attr.__init__(self)

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.sys = sys

    def collides(self, other):
        return isinstance(other, SpatialRegion)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return vars(self) == vars(other)

    def __hash__(self):
        return hash(tuple(vars(self).items()))


class Contains(attr.Attr):
    def __init__(self, *types):
        attr.Attr.__init__(self)
        self.types = types

    def collides(self, other):
        return False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return vars(self) == vars(other)

    def __hash__(self):
        return hash(tuple(vars(self).items()))


class _ComparisonParamAttrWrapper:
    def __init__(self, name):
        self.name = name

    def __lt__(self, other):
        return _ParamAttr(self.name, '<', other)

    def __le__(self, other):
        return _ParamAttr(self.name, '<=', other)

    def __gt__(self, other):
        return _ParamAttr(self.name, '>', other)

    def __ge__(self, other):
        return _ParamAttr(self.name, '>=', other)

    def __eq__(self, other):
        return _ParamAttr(self.name, '=', other)

    def __ne__(self, other):
        return _ParamAttr(self.name, '!=', other)


class _StringParamAttrWrapper(_ComparisonParamAttrWrapper):
    def like(self, other):
        return _ParamAttr(self.name, 'like', other)


class _NumberParamAttrWrapper(_ComparisonParamAttrWrapper):
    pass


# The walker is what traverses the attribute tree and converts it to a format
# that is understood by the server we are querying. The HEK walker builds up
# a dictionary of GET parameters to be sent to the server.
walker = attr.AttrWalker()


@walker.add_applier(Contains)
def _a(wlk, root, state, dct):
    dct['type'] = 'contains'
    if Contains not in state:
        state[Contains] = 1

    nid = state[Contains]
    n = 0
    for n, type_ in enumerate(root.types):
        dct['event_type{num:d}'.format(num=(nid + n))] = type_
    state[Contains] += n
    return dct


@walker.add_creator(
    Time, SpatialRegion, EventType, _ParamAttr, attr.AttrAnd, Contains)
def _c(wlk, root, state):
    value = {}
    wlk.apply(root, state, value)
    return [value]


@walker.add_applier(Time)
def _a(wlk, root, state, dct):
    dct['event_starttime'] = parse_time(root.start).strftime('%Y-%m-%dT%H:%M:%S')
    dct['event_endtime'] = parse_time(root.end).strftime('%Y-%m-%dT%H:%M:%S')
    return dct


@walker.add_applier(SpatialRegion)
def _a(wlk, root, state, dct):
    dct['x1'] = root.x1
    dct['y1'] = root.y1
    dct['x2'] = root.x2
    dct['y2'] = root.y2
    dct['event_coordsys'] = root.sys
    return dct


@walker.add_applier(EventType)
def _a(wlk, root, state, dct):
    if dct.get('type', None) == 'contains':
        raise ValueError
    dct['event_type'] = root.item
    return dct


@walker.add_applier(_ParamAttr)
def _a(wlk, root, state, dct):
    if _ParamAttr not in state:
        state[_ParamAttr] = 0

    nid = state[_ParamAttr]
    dct[f'param{nid:d}'] = root.name
    dct[f'op{nid:d}'] = root.op
    dct[f'value{nid:d}'] = root.value
    state[_ParamAttr] += 1
    return dct


@walker.add_applier(attr.AttrAnd)
def _a(wlk, root, state, dct):
    for attribute in root.attrs:
        wlk.apply(attribute, state, dct)


@walker.add_creator(attr.AttrOr)
def _c(wlk, root, state):
    blocks = []
    for attribute in root.attrs:
        blocks.extend(wlk.create(attribute, state))
    return blocks


@apply
class AR(EventType):
    CompactnessCls = _StringParamAttrWrapper('AR_CompactnessCls')
    IntensKurt = _StringParamAttrWrapper('AR_IntensKurt')
    IntensMax = _StringParamAttrWrapper('AR_IntensMax')
    IntensMean = _StringParamAttrWrapper('AR_IntensMean')
    IntensMin = _StringParamAttrWrapper('AR_IntensMin')
    IntensSkew = _StringParamAttrWrapper('AR_IntensSkew')
    IntensTotal = _StringParamAttrWrapper('AR_IntensTotal')
    IntensUnit = _StringParamAttrWrapper('AR_IntensUnit')
    IntensVar = _StringParamAttrWrapper('AR_IntensVar')
    McIntoshCls = _StringParamAttrWrapper('AR_McIntoshCls')
    MtWilsonCls = _StringParamAttrWrapper('AR_MtWilsonCls')
    NOAANum = _StringParamAttrWrapper('AR_NOAANum')
    NOAAclass = _StringParamAttrWrapper('AR_NOAAclass')
    NumSpots = _StringParamAttrWrapper('AR_NumSpots')
    PenumbraCls = _StringParamAttrWrapper('AR_PenumbraCls')
    Polarity = _StringParamAttrWrapper('AR_Polarity')
    SpotAreaRaw = _StringParamAttrWrapper('AR_SpotAreaRaw')
    SpotAreaRawUncert = _StringParamAttrWrapper('AR_SpotAreaRawUncert')
    SpotAreaRawUnit = _StringParamAttrWrapper('AR_SpotAreaRawUnit')
    SpotAreaRepr = _StringParamAttrWrapper('AR_SpotAreaRepr')
    SpotAreaReprUncert = _StringParamAttrWrapper('AR_SpotAreaReprUncert')
    SpotAreaReprUnit = _StringParamAttrWrapper('AR_SpotAreaReprUnit')
    ZurichCls = _StringParamAttrWrapper('AR_ZurichCls')

    def __init__(self):
        EventType.__init__(self, 'ar')


@apply
class CE(EventType):
    Accel = _StringParamAttrWrapper('CME_Accel')
    AccelUncert = _StringParamAttrWrapper('CME_AccelUncert')
    AccelUnit = _StringParamAttrWrapper('CME_AccelUnit')
    AngularWidth = _StringParamAttrWrapper('CME_AngularWidth')
    AngularWidthUnit = _StringParamAttrWrapper('CME_AngularWidthUnit')
    Mass = _StringParamAttrWrapper('CME_Mass')
    MassUncert = _StringParamAttrWrapper('CME_MassUncert')
    MassUnit = _StringParamAttrWrapper('CME_MassUnit')
    RadialLinVel = _StringParamAttrWrapper('CME_RadialLinVel')
    RadialLinVelMax = _StringParamAttrWrapper('CME_RadialLinVelMax')
    RadialLinVelMin = _StringParamAttrWrapper('CME_RadialLinVelMin')
    RadialLinVelStddev = _StringParamAttrWrapper('CME_RadialLinVelStddev')
    RadialLinVelUncert = _StringParamAttrWrapper('CME_RadialLinVelUncert')
    RadialLinVelUnit = _StringParamAttrWrapper('CME_RadialLinVelUnit')

    def __init__(self):
        EventType.__init__(self, 'ce')


@apply
class CD(EventType):
    Area = _StringParamAttrWrapper('CD_Area')
    AreaUncert = _StringParamAttrWrapper('CD_AreaUncert')
    AreaUnit = _StringParamAttrWrapper('CD_AreaUnit')
    Mass = _StringParamAttrWrapper('CD_Mass')
    MassUncert = _StringParamAttrWrapper('CD_MassUncert')
    MassUnit = _StringParamAttrWrapper('CD_MassUnit')
    Volume = _StringParamAttrWrapper('CD_Volume')
    VolumeUncert = _StringParamAttrWrapper('CD_VolumeUncert')
    VolumeUnit = _StringParamAttrWrapper('CD_VolumeUnit')

    def __init__(self):
        EventType.__init__(self, 'cd')


CH = EventType('ch')

CW = EventType('cw')


@apply
class FI(EventType):
    BarbsL = _StringParamAttrWrapper('FI_BarbsL')
    BarbsR = _StringParamAttrWrapper('FI_BarbsR')
    BarbsTot = _StringParamAttrWrapper('FI_BarbsTot')
    Chirality = _StringParamAttrWrapper('FI_Chirality')
    Length = _StringParamAttrWrapper('FI_Length')
    LengthUnit = _StringParamAttrWrapper('FI_LengthUnit')
    Tilt = _StringParamAttrWrapper('FI_Tilt')

    def __init__(self):
        EventType.__init__(self, 'fi')


FE = EventType('fe')

FA = EventType('fa')


@apply
class FL(EventType):
    EFoldTime = _StringParamAttrWrapper('FL_EFoldTime')
    EFoldTimeUnit = _StringParamAttrWrapper('FL_EFoldTimeUnit')
    Fluence = _StringParamAttrWrapper('FL_Fluence')
    FluenceUnit = _StringParamAttrWrapper('FL_FluenceUnit')
    GOESCls = _StringParamAttrWrapper('FL_GOESCls')
    PeakEM = _StringParamAttrWrapper('FL_PeakEM')
    PeakEMUnit = _StringParamAttrWrapper('FL_PeakEMUnit')
    PeakFlux = _StringParamAttrWrapper('FL_PeakFlux')
    PeakFluxUnit = _StringParamAttrWrapper('FL_PeakFluxUnit')
    PeakTemp = _StringParamAttrWrapper('FL_PeakTemp')
    PeakTempUnit = _StringParamAttrWrapper('FL_PeakTempUnit')

    def __init__(self):
        EventType.__init__(self, 'fl')


LP = EventType('lp')

OS = EventType('os')


@apply
class SS(EventType):
    SpinRate = _StringParamAttrWrapper('SS_SpinRate')
    SpinRateUnit = _StringParamAttrWrapper('SS_SpinRateUnit')

    def __init__(self):
        EventType.__init__(self, 'ss')


@apply
class EF(EventType):
    AspectRatio = _StringParamAttrWrapper('EF_AspectRatio')
    AxisLength = _StringParamAttrWrapper('EF_AxisLength')
    AxisOrientation = _StringParamAttrWrapper('EF_AxisOrientation')
    AxisOrientationUnit = _StringParamAttrWrapper('EF_AxisOrientationUnit')
    FluxUnit = _StringParamAttrWrapper('EF_FluxUnit')
    LengthUnit = _StringParamAttrWrapper('EF_LengthUnit')
    NegEquivRadius = _StringParamAttrWrapper('EF_NegEquivRadius')
    NegPeakFluxOnsetRate = _StringParamAttrWrapper('EF_NegPeakFluxOnsetRate')
    OnsetRateUnit = _StringParamAttrWrapper('EF_OnsetRateUnit')
    PosEquivRadius = _StringParamAttrWrapper('EF_PosEquivRadius')
    PosPeakFluxOnsetRate = _StringParamAttrWrapper('EF_PosPeakFluxOnsetRate')
    ProximityRatio = _StringParamAttrWrapper('EF_ProximityRatio')
    SumNegSignedFlux = _StringParamAttrWrapper('EF_SumNegSignedFlux')
    SumPosSignedFlux = _StringParamAttrWrapper('EF_SumPosSignedFlux')

    def __init__(self):
        EventType.__init__(self, 'ef')


CJ = EventType('cj')

PG = EventType('pg')

OT = EventType('ot')

NR = EventType('nr')


@apply
class SG(EventType):
    AspectRatio = _StringParamAttrWrapper('SG_AspectRatio')
    Chirality = _StringParamAttrWrapper('SG_Chirality')
    MeanContrast = _StringParamAttrWrapper('SG_MeanContrast')
    Orientation = _StringParamAttrWrapper('SG_Orientation')
    PeakContrast = _StringParamAttrWrapper('SG_PeakContrast')
    Shape = _StringParamAttrWrapper('SG_Shape')

    def __init__(self):
        EventType.__init__(self, 'sg')


SP = EventType('sp')

CR = EventType('cr')


@apply
class CC(EventType):
    AxisUnit = _StringParamAttrWrapper('CC_AxisUnit')
    MajorAxis = _StringParamAttrWrapper('CC_MajorAxis')
    MinorAxis = _StringParamAttrWrapper('CC_MinorAxis')
    TiltAngleMajorFromRadial = _StringParamAttrWrapper('CC_TiltAngleMajorFromRadial')
    TiltAngleUnit = _StringParamAttrWrapper('CC_TiltAngleUnit')

    def __init__(self):
        EventType.__init__(self, 'cc')


ER = EventType('er')


@apply
class TO(EventType):
    Shape = _StringParamAttrWrapper('TO_Shape')

    def __init__(self):
        EventType.__init__(self, 'to')


@apply
class Wave:
    DisplMaxAmpl = _StringParamAttrWrapper('WaveDisplMaxAmpl')
    DisplMinAmpl = _StringParamAttrWrapper('WaveDisplMinAmpl')
    DisplUnit = _StringParamAttrWrapper('WaveDisplUnit')
    lMaxPower = _StringParamAttrWrapper('WavelMaxPower')
    lMaxPowerUncert = _StringParamAttrWrapper('WavelMaxPowerUncert')
    lMaxRange = _StringParamAttrWrapper('WavelMaxRange')
    lMinRange = _StringParamAttrWrapper('WavelMinRange')
    lUnit = _StringParamAttrWrapper('WavelUnit')


@apply
class Veloc:
    MaxAmpl = _StringParamAttrWrapper('VelocMaxAmpl')
    MaxPower = _StringParamAttrWrapper('VelocMaxPower')
    MaxPowerUncert = _StringParamAttrWrapper('VelocMaxPowerUncert')
    MinAmpl = _StringParamAttrWrapper('VelocMinAmpl')
    Unit = _StringParamAttrWrapper('VelocUnit')


@apply
class Freq:
    MaxRange = _StringParamAttrWrapper('FreqMaxRange')
    MinRange = _StringParamAttrWrapper('FreqMinRange')
    PeakPower = _StringParamAttrWrapper('FreqPeakPower')
    Unit = _StringParamAttrWrapper('FreqUnit')


@apply
class Intens:
    MaxAmpl = _StringParamAttrWrapper('IntensMaxAmpl')
    MinAmpl = _StringParamAttrWrapper('IntensMinAmpl')
    Unit = _StringParamAttrWrapper('IntensUnit')


@apply
class Area:
    AtDiskCenter = _StringParamAttrWrapper('Area_AtDiskCenter')
    AtDiskCenterUncert = _StringParamAttrWrapper('Area_AtDiskCenterUncert')
    Raw = _StringParamAttrWrapper('Area_Raw')
    Uncert = _StringParamAttrWrapper('Area_Uncert')
    Unit = _StringParamAttrWrapper('Area_Unit')


@apply
class BoundBox:
    C1LL = _StringParamAttrWrapper('BoundBox_C1LL')
    C1UR = _StringParamAttrWrapper('BoundBox_C1UR')
    C2LL = _StringParamAttrWrapper('BoundBox_C2LL')
    C2UR = _StringParamAttrWrapper('BoundBox_C2UR')


@apply
class Bound:
    ox_C1LL = _StringParamAttrWrapper('BoundBox_C1LL')
    ox_C1UR = _StringParamAttrWrapper('BoundBox_C1UR')
    ox_C2LL = _StringParamAttrWrapper('BoundBox_C2LL')
    ox_C2UR = _StringParamAttrWrapper('BoundBox_C2UR')
    CCNsteps = _StringParamAttrWrapper('Bound_CCNsteps')
    CCStartC1 = _StringParamAttrWrapper('Bound_CCStartC1')
    CCStartC2 = _StringParamAttrWrapper('Bound_CCStartC2')


@apply
class OBS:
    ChannelID = _StringParamAttrWrapper('OBS_ChannelID')
    DataPrepURL = _StringParamAttrWrapper('OBS_DataPrepURL')
    FirstProcessingDate = _StringParamAttrWrapper('OBS_FirstProcessingDate')
    IncludesNRT = _StringParamAttrWrapper('OBS_IncludesNRT')
    Instrument = _StringParamAttrWrapper('OBS_Instrument')
    LastProcessingDate = _StringParamAttrWrapper('OBS_LastProcessingDate')
    LevelNum = _StringParamAttrWrapper('OBS_LevelNum')
    MeanWavel = _StringParamAttrWrapper('OBS_MeanWavel')
    Observatory = _StringParamAttrWrapper('OBS_Observatory')
    Title = _StringParamAttrWrapper('OBS_Title')
    WavelUnit = _StringParamAttrWrapper('OBS_WavelUnit')


@apply
class Skel:
    Curvature = _StringParamAttrWrapper('Skel_Curvature')
    Nsteps = _StringParamAttrWrapper('Skel_Nsteps')
    StartC1 = _StringParamAttrWrapper('Skel_StartC1')
    StartC2 = _StringParamAttrWrapper('Skel_StartC2')


@apply
class FRM:
    Contact = _StringParamAttrWrapper('FRM_Contact')
    HumanFlag = _StringParamAttrWrapper('FRM_HumanFlag')
    Identifier = _StringParamAttrWrapper('FRM_Identifier')
    Institute = _StringParamAttrWrapper('FRM_Institute')
    Name = _StringParamAttrWrapper('FRM_Name')
    ParamSet = _StringParamAttrWrapper('FRM_ParamSet')
    SpecificID = _StringParamAttrWrapper('FRM_SpecificID')
    URL = _StringParamAttrWrapper('FRM_URL')
    VersionNumber = _StringParamAttrWrapper('FRM_VersionNumber')


@apply
class Event:
    C1Error = _StringParamAttrWrapper('Event_C1Error')
    C2Error = _StringParamAttrWrapper('Event_C2Error')
    ClippedSpatial = _StringParamAttrWrapper('Event_ClippedSpatial')
    ClippedTemporal = _StringParamAttrWrapper('Event_ClippedTemporal')
    Coord1 = _StringParamAttrWrapper('Event_Coord1')
    Coord2 = _StringParamAttrWrapper('Event_Coord2')
    Coord3 = _StringParamAttrWrapper('Event_Coord3')
    CoordSys = _StringParamAttrWrapper('Event_CoordSys')
    CoordUnit = _StringParamAttrWrapper('Event_CoordUnit')
    MapURL = _StringParamAttrWrapper('Event_MapURL')
    MaskURL = _StringParamAttrWrapper('Event_MaskURL')
    Npixels = _StringParamAttrWrapper('Event_Npixels')
    PixelUnit = _StringParamAttrWrapper('Event_PixelUnit')
    Probability = _StringParamAttrWrapper('Event_Probability')
    TestFlag = _StringParamAttrWrapper('Event_TestFlag')
    Type = _StringParamAttrWrapper('Event_Type')


@apply
class Outflow:
    Length = _StringParamAttrWrapper('Outflow_Length')
    LengthUnit = _StringParamAttrWrapper('Outflow_LengthUnit')
    OpeningAngle = _StringParamAttrWrapper('Outflow_OpeningAngle')
    Speed = _StringParamAttrWrapper('Outflow_Speed')
    SpeedUnit = _StringParamAttrWrapper('Outflow_SpeedUnit')
    TransSpeed = _StringParamAttrWrapper('Outflow_TransSpeed')
    Width = _StringParamAttrWrapper('Outflow_Width')
    WidthUnit = _StringParamAttrWrapper('Outflow_WidthUnit')


@apply
class Misc:
    KB_Archivist = _StringParamAttrWrapper('KB_Archivist')
    MaxMagFieldStrength = _StringParamAttrWrapper('MaxMagFieldStrength')
    MaxMagFieldStrengthUnit = _StringParamAttrWrapper('MaxMagFieldStrengthUnit')
    OscillNPeriods = _StringParamAttrWrapper('OscillNPeriods')
    OscillNPeriodsUncert = _StringParamAttrWrapper('OscillNPeriodsUncert')
    PeakPower = _StringParamAttrWrapper('PeakPower')
    PeakPowerUnit = _StringParamAttrWrapper('PeakPowerUnit')
    RasterScanType = _StringParamAttrWrapper('RasterScanType')
