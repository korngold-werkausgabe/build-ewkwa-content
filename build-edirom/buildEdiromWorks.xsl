<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:mei="http://www.music-encoding.org/ns/mei" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs mei" version="2.0">
  
  <xsl:output indent="yes"/>
  
  <xsl:param name="annots" select="''" />
  <xsl:param name="workUUID" select="''" />
  <xsl:param name="workTitle" select="''" />
  <xsl:param name="editionTitle" select="''" />
  
  <xsl:template match="mei:mei">
    <mei:mei xmlns="http://www.music-encoding.org/ns/mei" xml:id="{$uuid[@name='editionWork']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </mei:mei>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$workTitle"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:editionStmt/mei:edition">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$editionTitle"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work">
    <xsl:element name="work" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:id"><xsl:value-of select="$workUUID"/></xsl:attribute>
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </xsl:element>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:title">
    <xsl:element name="title" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:lang">de</xsl:attribute>
      <xsl:value-of select="$workTitle"/>
    </xsl:element>
    <xsl:element name="title" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:lang">en</xsl:attribute>
      <xsl:value-of select="$workTitle"/>
    </xsl:element>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:notesStmt">
    <xsl:element name="notesStmt" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:copy-of select="$annots"/>
    </xsl:element>
  </xsl:template>
    
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()" />
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>